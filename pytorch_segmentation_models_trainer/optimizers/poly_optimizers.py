# -*- coding: utf-8 -*-
"""
/***************************************************************************
 pytorch_segmentation_models_trainer
                              -------------------
        begin                : 2021-04-07
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Philipe Borba - Cartographic Engineer 
                                                            @ Brazilian Army
        email                : philipeborba at gmail dot com
 ***************************************************************************/
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 *   Code inspired by the one in                                           *
 *   https://github.com/Lydorn/Polygonization-by-Frame-Field-Learning/     *
 ****
"""

import torch
from pytorch_segmentation_models_trainer.custom_losses.crossfield_losses import AlignLoss

class TensorPolyOptimizer:
    def __init__(
        self,
        config,
        tensorpoly,
        indicator,
        c0c2,
        data_coef,
        length_coef,
        crossfield_coef,
        dist=None,
        dist_coef=None
    ):
        assert len(indicator.shape) == 3, "indicator: (N, H, W)"
        assert len(c0c2.shape) == 4 and c0c2.shape[1] == 4, "c0c2: (N, 4, H, W)"
        if dist is not None:
            assert len(dist.shape) == 3, "dist: (N, H, W)"


        self.config = config
        self.tensorpoly = tensorpoly

        # Require grads for graph.pos: this is what is optimized
        self.tensorpoly.pos.requires_grad = True

        # Save pos of endpoints so that they can be reset after each step (endpoints are not meant to be moved)
        self.endpoint_pos = self.tensorpoly.pos[self.tensorpoly.is_endpoint].clone()

        self.criterion = PolygonAlignLoss(
            indicator,
            config["data_level"],
            c0c2,
            data_coef,
            length_coef,
            crossfield_coef,
            dist=dist,
            dist_coef=dist_coef
        )
        self.optimizer = torch.optim.SGD([tensorpoly.pos], lr=config["poly_lr"])

        def lr_warmup_func(iter):
            if iter < config["warmup_iters"]:
                coef = 1 + (config["warmup_factor"] - 1) * (config["warmup_iters"] - iter) / config["warmup_iters"]
            else:
                coef = 1
            return coef

        self.lr_scheduler = torch.optim.lr_scheduler.LambdaLR(
            self.optimizer,
            lr_lambda=lr_warmup_func
        )

    def step(self, iter_num):
        self.optimizer.zero_grad()
        loss, losses_dict = self.criterion(self.tensorpoly)
        # print("loss:", loss.item())
        loss.backward()
        # print(polygon_tensor.grad[0])
        self.optimizer.step()
        self.lr_scheduler.step(iter_num)

        # Move endpoints back:
        with torch.no_grad():
            self.tensorpoly.pos[self.tensorpoly.is_endpoint] = self.endpoint_pos
        return loss.item(), losses_dict

    def optimize(self):
        optim_iter = range(self.config["steps"])
        for iter_num in optim_iter:
            loss, losses_dict = self.step(iter_num)
        return self.tensorpoly

class PolygonAlignLoss:
    def __init__(
            self,
            indicator,
            level,
            c0c2,
            data_coef,
            length_coef,
            crossfield_coef,
            dist=None,
            dist_coef=None
    ):
        self.indicator = indicator
        self.level = level
        self.c0c2 = c0c2
        self.dist = dist

        self.data_coef = data_coef
        self.length_coef = length_coef
        self.crossfield_coef = crossfield_coef
        self.dist_coef = dist_coef

    def __call__(self, tensorpoly):
        """

        :param tensorpoly: closed polygon
        :return:
        """
        polygon = tensorpoly.pos[tensorpoly.to_padded_index]
        polygon_batch = tensorpoly.batch[tensorpoly.to_padded_index]

        # Compute edges:
        edges = polygon[1:] - polygon[:-1]
        # Compute edge mask to remove edges that connect two different polygons from loss
        # Also note the last poly_slice is not used, because the last edge of the last polygon is not connected to a non-existant next polygon:
        edge_mask = torch.ones((edges.shape[0]), device=edges.device)
        edge_mask[tensorpoly.to_unpadded_poly_slice[:-1, 1]] = 0

        midpoints = (polygon[1:] + polygon[:-1]) / 2
        midpoints_batch = polygon_batch[1:]

        midpoints_int = midpoints.round().long()
        midpoints_int[:, 0] = torch.clamp(midpoints_int[:, 0], 0, self.c0c2.shape[2] - 1)
        midpoints_int[:, 1] = torch.clamp(midpoints_int[:, 1], 0, self.c0c2.shape[3] - 1)
        midpoints_c0 = self.c0c2[midpoints_batch, :2, midpoints_int[:, 0], midpoints_int[:, 1]]
        midpoints_c2 = self.c0c2[midpoints_batch, 2:, midpoints_int[:, 0], midpoints_int[:, 1]]

        norms = torch.norm(edges, dim=-1)
        # Add edges with small norms to the edge mask so that losses are not computed on them
        edge_mask[norms < 0.1] = 0  # Less than 10% of a pixel
        z = edges / (norms[:, None] + 1e-3)

        # Align to crossfield
        align_loss = frame_field_utils.framefield_align_error(midpoints_c0, midpoints_c2, z, complex_dim=1)
        align_loss = align_loss * edge_mask
        total_align_loss = torch.sum(align_loss)

        # Align to level set of indicator:
        pos_indicator_value = bilinear_interpolate(self.indicator[:, None, ...], tensorpoly.pos, batch=tensorpoly.batch)
        # TODO: Try to use grid_sample with batch for speed: put batch dim to height dim and make a single big image.
        # TODO: Convert pos accordingly and take care of borders
        # height = self.indicator.shape[1]
        # width = self.indicator.shape[2]
        # normed_xy = tensorpoly.pos.roll(shifts=1, dims=-1)
        # normed_xy[: 0] /= (width-1)
        # normed_xy[: 1] /= (height-1)
        # centered_xy = 2*normed_xy - 1
        # pos_value = torch.nn.functional.grid_sample(self.indicator[None, None, ...], centered_batch_xy[None, None, ...], align_corners=True).squeeze()
        level_loss = torch.sum(torch.pow(pos_indicator_value - self.level, 2))

        # Align to minimum distance from the boundary
        dist_loss = None
        if self.dist is not None:
            pos_dist_value = bilinear_interpolate(self.dist[:, None, ...], tensorpoly.pos, batch=tensorpoly.batch)
            dist_loss = torch.sum(torch.pow(pos_dist_value, 2))

        length_penalty = torch.sum(
            torch.pow(norms * edge_mask, 2))  # Sum of squared norm to penalise uneven edge lengths
        # length_penalty = torch.sum(norms)

        losses_dict = {
            "align": total_align_loss.item(),
            "level": level_loss.item(),
            "length": length_penalty.item(),
        }
        coef_sum = self.data_coef + self.length_coef + self.crossfield_coef
        total_loss = (self.data_coef * level_loss + self.length_coef * length_penalty + self.crossfield_coef * total_align_loss)
        if dist_loss is not None:
            losses_dict["dist"] = dist_loss.item()
            total_loss += self.dist_coef * dist_loss
            coef_sum += self.dist_coef
        total_loss /= coef_sum
        return total_loss, losses_dict
