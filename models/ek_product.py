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

    def generate_code(self):
        """Generating default code for ek products"""

        # Generate a random 6-digit number
        random_number = random.randint(100000, 999999)

        # Concatenate the "eki_" and random number
        product_code = f"eki_{random_number}"

        return product_code


    # set the url and headers
    headers = {"Content-Type": "application/json", "Accept": "application/json", "Catch-Control": "no-cache"}

    @api.model
    def create(self, vals):
        logging.warning("create product ======")
        logging.warning(vals)
        # 1- CREATE A PRODUCT FROM ekiclik
        domain = "https://ekiclik.admin.wissal-group.com"
        url_product = "/api/odoo/products"

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
            self.default_code = self.generate_code()
            if "image_url" in vals and vals["image_url"]:
                image = base64.b64encode(requests.get(vals["image_url"]).content)
                vals["image_1920"] = image
                vals.pop("image_url")

            rec = super(Product, self).create(vals)

            product_json = {
                "name": rec.name,
                "description": rec.description,
                "categoryName": rec.categ_id.name,
                "brand": {
                    "name": rec.brand_id.name,
                    "reference": ""
                },
                "refConstructor": rec.default_code,
                "manufactureName": "",
                "activate": True,
                "configurations": []
            }
            configurations = []

            for record in rec:
                if record.product_template_variant_value_ids:
                    configuration = {
                        'name': rec.name,
                        "reference": rec.default_code,
                        "price": rec.list_price,
                        "buyingPrice": 0,
                        "state": "Active",
                        "productCharacteristics": [],
                        "images": rec.image_url,
                        # "certificateUrl": record.certificate_url,
                        "active": True,
                        "description": rec.description,
                    }

                    for value in rec.product_template_variant_value_ids:
                        product_characteristic = {
                            "value": value.value_ids,
                            "name": value.attribute_id
                        }
                        configuration["productCharacteristics"].append(product_characteristic)

                    configurations.append(configuration)
            product_json["configurations"] = configurations
            _logger.info(
                    '\n\n\n PRODUCT BODY JSON\n\n\n\n--->>  %s\n\n\n\n', product_json)
            response = requests.post(domain + url_product, data=json.dumps(product_json),
                                     headers=self.headers)
            _logger.info('\n\n\n(CREATE product) response from eki \n\n\n\n--->  %s\n\n\n\n',
                         response.content)

            return rec

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
