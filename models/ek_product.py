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
    manufacture_name = fields.Char(string='Fabricant')

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

        # 2- CREATE A PRODUCT FROM ODOO (Send a product to ekiclik)
        else:
            if "image_url" in vals and vals["image_url"]:
                image = base64.b64encode(requests.get(vals["image_url"]).content)
                vals["image_1920"] = image
                vals.pop("image_url")

            rec = super(Product, self).create(vals)
            product_json ={
                "name": rec.name,
                "description": rec.description,
                "categoryName": rec.categ_id.name,
                "brand": {
                    "name": rec.brand_id.name,
                    "reference": ""
                },
                "refConstructor": "rc_" + str(rec.id),
                "manufactureName": rec.manufacture_name,
                "activate": True,
                "configurations": []

            }
            variantes = self.env['product.product'].search([('name', '=', rec.name)])
            for record in variantes :
                configurations = []

                if record.product_template_attribute_value_ids:
                    configuration = {
                        'name': record.name,
                        "description": '',
                        "reference": record.default_code,
                        "price": record.lst_price,
                        "buyingPrice": 0,
                        "state": "Active",
                        "productCharacteristics": [],
                        "image": rec.image_url if rec.image_url else '',
                        #"certificateUrl":record.certificate_url,

                    }
                    for value in record.product_template_attribute_value_ids:
                        product_characteristic = {
                            "name": value.attribute_id.name if value.attribute_id else '',
                            "value": value.product_attribute_value_id.name if value.product_attribute_value_id else ''
                        }
                        configurations.append(configuration)
                        configuration["productCharacteristics"].append(product_characteristic)

                product_json["configurations"].append(configurations)
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

class EkiProduct(models.Model):
    _inherit = ['product.product']

    manufacture_name = fields.Char(string='Fabricant')

    def generate_code(self):
        """Generating default code for ek products"""

        # Generate a random 6-digit number
        random_number = random.randint(100000, 999999)

        # Concatenate the "eki_" and random number
        product_code = f"eki_{random_number}"

        return product_code



    @api.model
    def create(self, vals):

        vals["default_code"] = self.generate_code()

        rec = super(EkiProduct, self).create(vals)


        return rec
