import re

from odoo import models, fields, api, _, exceptions
import logging
import json
import requests
from .config import *
from odoo.tools.float_utils import float_compare, float_is_zero, float_round

from odoo.exceptions import ValidationError, UserError
from odoo.http import request

_logger = logging.getLogger(__name__)


class EkQuant(models.Model):
    _inherit = "stock.quant"

    headers = {"Content-Type": "application/json","Accept": "application/json", "Catch-Control": "no-cache"}
    url_stock = '/api/odoo/stocks'

    def action_apply_inventory(self):
        domain = ""
        domain_cpa = ""
        config_settings = self.env['res.config.settings'].search([], order='id desc', limit=1)
        if config_settings:
            domain = config_settings.domain
            domain_cpa = config_settings.domain_cpa
        _logger.info(
            '\n\n\nDOMAAIN\n\n\n\n--->>  %s\n\n\n\n', domain)
        products_tracked_without_lot = []
        for quant in self:
            rounding = quant.product_uom_id.rounding
            if fields.Float.is_zero(quant.inventory_diff_quantity, precision_rounding=rounding) \
                    and fields.Float.is_zero(quant.inventory_quantity, precision_rounding=rounding) \
                    and fields.Float.is_zero(quant.quantity, precision_rounding=rounding):
                continue
            if quant.product_id.tracking in ['lot', 'serial'] and \
                    not quant.lot_id and quant.inventory_quantity != quant.quantity:
                products_tracked_without_lot.append(quant.product_id.id)
        # for some reason if multi-record, env.context doesn't pass to wizards...
        ctx = dict(self.env.context or {})
        ctx['default_quant_ids'] = self.ids
        quants_outdated = self.filtered(lambda quant: quant.is_outdated)
        if quants_outdated:
            ctx['default_quant_to_fix_ids'] = quants_outdated.ids
            return {
                'name': _('Conflict in Inventory Adjustment'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'views': [(False, 'form')],
                'res_model': 'stock.inventory.conflict',
                'target': 'new',
                'context': ctx,
            }
        if products_tracked_without_lot:
            ctx['default_product_ids'] = products_tracked_without_lot
            return {
                'name': _('Tracked Products in Inventory Adjustment'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'views': [(False, 'form')],
                'res_model': 'stock.track.confirmation',
                'target': 'new',
                'context': ctx,
            }
        self._apply_inventory()
        self.inventory_quantity_set = False

        line_product = self.env['product.product'].search([('id', '=', self.product_id.product_variant_id.id)])
        if self.location_id.company_id.name == "Centrale des Achats":
            numeric_value = ""
            if self.product_id.tax_string:
                pattern = r'(\d[\d\s,.]+)'

                # Use the findall function to extract all matches
                matches = re.findall(pattern, self.product_id.tax_string)

                # Join the matches into a single string (if there are multiple matches)
                numeric_value = ''.join(matches)

                # Replace commas with dots (if necessary)
                numeric_value = numeric_value.replace(',', '.')

                # Remove non-breaking space characters
                numeric_value = numeric_value.replace('\xa0', '')

            else:
                numeric_value = self.product_id.lst_price
            json_obj = [{
                        "pos": "EKIWH",
                        "configuration_ref_odoo": self.product_id.ref_odoo,
                        "realQuantity": self.quantity,
                        "price": numeric_value}]
            _logger.info(
                '\n\n\n sending stock.picking to ek \n\n\n\n--->>  %s\n\n\n\n', json_obj)
            response1 = requests.put(str(domain) + self.url_stock, data=json.dumps(json_obj),
                                     headers=self.headers)
            _logger.info(
                '\n\n\n response \n\n\n\n--->>  %s\n\n\n\n', response1)
            response_cpa = requests.put(str(domain_cpa) + self.url_stock, data=json.dumps(json_obj),
                                     headers=self.headers)
            _logger.info(
                '\n\n\n response cpa \n\n\n\n--->>  %s\n\n\n\n', response_cpa)
            return response1, response_cpa
        else:
            numeric_value = ""
            if self.product_id.tax_string:
                pattern = r'(\d[\d\s,.]+)'

                # Use the findall function to extract all matches
                matches = re.findall(pattern, self.product_id.tax_string)

                # Join the matches into a single string (if there are multiple matches)
                numeric_value = ''.join(matches)

                # Replace commas with dots (if necessary)
                numeric_value = numeric_value.replace(',', '.')

                # Remove non-breaking space characters
                numeric_value = numeric_value.replace('\xa0', '')

            else:
                numeric_value = self.product_id.lst_price
            json_obj_pdv = [{
                        "pos": self.location_id.company_id.codification,
                        "configuration_ref_odoo": self.product_id.ref_odoo,
                        "realQuantity": self.quantity,
                        "price": self.product_id.lst_price}]



            _logger.info(
                    '\n\n\n sending stock.picking to PDV \n\n\n\n--->>  %s\n\n\n\n', json_obj_pdv)
            response2 = requests.put(str(domain) + self.url_stock, data=json.dumps(json_obj_pdv),
                                         headers=self.headers)
            _logger.info(
                '\n\n\n response \n\n\n\n--->>  %s\n\n\n\n', response2)
            response2_cpa = requests.put(str(domain_cpa) + self.url_stock, data=json.dumps(json_obj_pdv),
                                         headers=self.headers)
            _logger.info(
                '\n\n\n response \n\n\n\n--->>  %s\n\n\n\n', response2_cpa)
            return response2, response2_cpa




