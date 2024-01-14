import json
import requests
from odoo import models, fields, api, exceptions
from odoo.http import request
import logging
from _datetime import datetime
from odoo.exceptions import ValidationError
from .config import *
import base64
import random
import string

_logger = logging.getLogger(__name__)


class Product(models.Model):
    _inherit = ['product.template']

    create_by = fields.Char(string="Créé à partir de",readonly=True)
    brand = fields.Many2one("product.brand", 'Marque')
    image_url = fields.Char(string='Image URL')


    # set the url and headers
    headers = {"Content-Type": "application/json", "Accept": "application/json", "Catch-Control": "no-cache"}

    @api.model
    def create(self, vals):
        logging.warning("create product ======")
        logging.warning(vals)
        # 1- CREATE A PRODUCT FROM ekiclik
        domain = "https://apiadmin-odoo.ekiclik.com"
        url_product=""

        if 'create_by' in vals.keys() and vals['create_by'] != 'Odoo':
            if 'barcode' in vals and not vals['barcode']:
                vals.pop('barcode')

            vals['create_by'] = "Ekiclik"
            if "brand" in vals and vals["brand"]:
                brand = self.env['product.brand'].search([('name', '=', vals['brand'])])
                if brand:
                    vals['brand_id'] = brand.id
                else:
                    brand = self.env['product.brand'].create({
                        'name': vals['brand']
                    })
                    vals['brand_id'] = brand.id
            vals.pop('brand')
            if "list_price" in vals and not vals["list_price"]:
                vals.pop('list_price')

            if 'category' in vals and vals['category']:
                # Get the category record
                category = self.env['product.category'].search([('name', '=', vals['category'])])
                if category:
                   vals['categ_id'] = category.id
                else:
                    category = self.env['product.category'].create({
                        'name': vals['category']
                    })
                    vals['categ_id'] = category.id
            vals.pop('category')
            # GET IMAGE URL AND AUTOMATICALLY DISPLAY IT ON ODOO
            if "image_url" in vals and vals["image_url"]:
                image = base64.b64encode(requests.get(vals["image_url"]).content)
                vals["image_1920"] = image
                vals.pop("image_url")

            rec = super(Product, self).create(vals)

            return rec

        # 2- CREATE A PRODUCT FROM ODOO (Send a product to Imtech)
        else:
            if "image_url" in vals and vals["image_url"]:
                image = base64.b64encode(requests.get(vals["image_url"]).content)
                vals["image_1920"] = image
                vals.pop("image_url")
            rec = super(Product, self).create(vals)

            return rec

    @api.model
    def write(self, vals):
        _logger.info(
            '\n\n\n update\n\n\n\n--->>  %s\n\n\n\n', vals)
        if 'create_by' in vals.keys() and vals['create_by'] != 'Odoo':
            _logger.info(
                '\n\n\ncreate_by\n\n\n\n--->>  %s\n\n\n\n', vals["create_by"])
            if 'barcode' in vals and not vals['barcode']:
                vals.pop('barcode')

            vals['create_by'] = "Ekiclik"
            if "brand" in vals and vals["brand"]:
                brand = self.env['product.brand'].search([('name', '=', vals['brand'])])
                if brand:
                    vals['brand_id'] = brand.id
                else:
                    brand = self.env['product.brand'].create({
                        'name': vals['brand']
                    })
                    vals['brand_id'] = brand.id
            vals.pop('brand')
            if "list_price" in vals and not vals["list_price"]:
                vals.pop('list_price')

            if 'category' in vals and vals['category']:
                # Get the category record
                category = self.env['product.category'].search([('name', '=', vals['category'])])
                if category:
                   vals['categ_id'] = category.id
                else:
                    category = self.env['product.category'].create({
                        'name': vals['category']
                    })
                    vals['categ_id'] = category.id
            vals.pop('category')
            # GET IMAGE URL AND AUTOMATICALLY DISPLAY IT ON ODOO
            if "image_url" in vals and vals["image_url"]:
                image = base64.b64encode(requests.get(vals["image_url"]).content)
                vals["image_1920"] = image
                vals.pop("image_url")
            _logger.info(
                '\n\n\n update\n\n\n\n--->>  %s\n\n\n\n', vals)
            rec = super(Product, self).write(vals)

            _logger.info(
                '\n\n\nwriting on product with vals\n\n\n\n--->>  %s\n\n\n\n', vals)

            return rec
        else:

           rec = super(Product, self).write(vals)

           return rec
