/*
 * Project      : VLSIT ASIC VIP Design AI Flow
 * Author       : <USER_NAME> (user)
 * AI Flow      : VLSIT ASIC VIP Design AI Flow
 * AI Flow Page : https://github.com/nguyenquanicd/VLSIT_ASIC_VIP_DESIGN_AI_FLOW
 * Date         : 2026-10-10
 * Description  : Common types of the VLSIT VIP base package. Included inside the package.
 */
// SPDX-License-Identifier: Apache-2.0

// Interface mode of an agent: the host starts transfers, the device answers them.
typedef enum bit {
  VIP_HOST   = 1'b0,
  VIP_DEVICE = 1'b1
} vlsit_vip_if_mode_e;
