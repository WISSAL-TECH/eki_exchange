import json
import sys

import requests
#from minio import Minio

from odoo import models, fields, api, exceptions
from odoo.http import request
import logging
from _datetime import datetime
from odoo.exceptions import ValidationError

from urllib.parse import quote
from io import BytesIO ,StringIO
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
    certificate = fields.Binary("Certificat")
    certificate_url = fields.Char("Certificate URL", compute='_compute_certificate_url')

    @api.depends('certificate')
    def _compute_certificate_url(self):
        for record in self:
             record.certificate_url = ''
    # set the url and headers
    headers = {"Content-Type": "application/json", "Accept": "application/json", "Catch-Control": "no-cache"}

    @api.model
    def create(self, vals):
        logging.warning("create product ======")
        logging.warning(vals)
        # 1- CREATE A PRODUCT FROM ekiclik
        domain = ""
        config_settings = self.env['res.config.settings'].search([], order='id desc', limit=1)
        if config_settings:
            domain = config_settings.domain
        _logger.info(
            '\n\n\nDOMAAIN\n\n\n\n--->>  %s\n\n\n\n', domain)
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
                    "reference": "br_"+str(rec.brand_id.id)
                },
                "refConstructor": "rc_" + str(rec.id),
                "manufactureName": rec.manufacture_name,
                "activate": True,

            }
            variantes = self.env['product.product'].search([('name', '=', rec.name)])
            configurations = []

            for record in variantes :
                if record.product_template_attribute_value_ids:
                    configuration = {
                        'name': record.name,
                        "description": '',
                        "reference": record.default_code,
                        "price": record.lst_price,
                        "buyingPrice": 0,
                        #"state": "Active",
                        "productCharacteristics": [],
                        "images": rec.image_url if rec.image_url else 'image_url',
                        "active": True,
                        "certificateUrl": record.certificate_url,
                    }

                    for value in record.product_template_attribute_value_ids:
                        product_characteristic = {
                            "name": value.attribute_id.name if value.attribute_id else '',
                            "value": value.product_attribute_value_id.name if value.product_attribute_value_id else ''
                        }
                        configuration["productCharacteristics"].append(product_characteristic)
                    configurations.append(configuration)

            product_json["configurations"] = configurations
            _logger.info(
                '\n\n\n PRODUCT BODY JSON\n\n\n\n--->>  %s\n\n\n\n', product_json)
            response = requests.post(str(domain)+str(url_product), data=json.dumps(product_json),
                                     headers=self.headers)
            _logger.info('\n\n\n(CREATE product) response from eki \n\n\n\n--->  %s\n\n\n\n',
                         response.content)

            return rec

    def create_doc_url(self, attach):
        client = Minio("play.min.io",
                       access_key="admin",
                       secret_key="d%gHsjnZ*eD")
        bucket_name = "file-storage-document-salam"
        destination_file = "eki_file"+str(attach.id)

        if attach.datas:
            data_fileobj = BytesIO(base64.standard_b64decode(attach.datas))

            client.fput_object(
               bucket_name, destination_file, data_fileobj,
            )

            # Get the URL for the uploaded file
            url = client.presigned_get_object(bucket_name, destination_file)

            print(
                data_fileobj, "successfully uploaded as object",
                destination_file, "to bucket", bucket_name,
            )

            attach.write({'url': url})

    def write(self, vals):
        domain = ""
        config_settings = self.env['res.config.settings'].search([], order='id desc', limit=1)
        if config_settings:
            domain = config_settings.domain
        _logger.info(
            '\n\n\nDOMAAIN\n\n\n\n--->>  %s\n\n\n\n', domain)
        url_archive_product = "/api/odoo/products/archive/"
        url_activate_product = "/api/odoo/products/activate/"

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
            if "active" in vals and vals["active"] == False:
                # send archive product to ekiclik
                _logger.info('\n\n\n Archive PRODUCT \n\n\n\n--->>  %s\n\n\n\n')
                response = requests.patch(str(domain) + str(url_archive_product) + "rc_" + str(self.id),
                                          headers=self.headers)

                _logger.info('\n\n\n(archive product) response from eki \n\n\n\n--->  %s\n\n\n\n',
                             response.content)
            if "active" in vals and vals["active"] == True:
                # send activate product to ekiclik
                _logger.info('\n\n\n Activate PRODUCT \n\n\n\n--->>  %s\n\n\n\n')
                response = requests.patch(str(domain) + str(url_activate_product) + "rc_" + str(self.id),
                                          headers=self.headers)

                _logger.info('\n\n\n(activate product) response from eki \n\n\n\n--->  %s\n\n\n\n',
                             response.content)


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

    def write(self, vals):
        domain = ""
        config_settings = self.env['res.config.settings'].search([], order='id desc', limit=1)
        if config_settings:
            domain = config_settings.domain
        _logger.info(
            '\n\n\nDOMAAIN\n\n\n\n--->>  %s\n\n\n\n', domain)
        url_archive_product = "/api/odoo/products/configuration/archive/"
        url_activate_product = "/api/odoo/products/configuration/activate"

        _logger.info(
            '\n\n\n update\n\n\n\n--->>  %s\n\n\n\n', vals)

        if "active" in vals and vals["active"] == False:
                # send archive product to ekiclik
                _logger.info('\n\n\n Archive VARIANTE \n\n\n\n--->>  %s\n\n\n\n')
                response = requests.patch(str(domain) + str(url_archive_product) + "rc_" + str(self.id),
                                          headers=self.headers)

                _logger.info('\n\n\n(archive variante) response from eki \n\n\n\n--->  %s\n\n\n\n',
                             response.content)
        if "active" in vals and vals["active"] == True:
                # send activate product to ekiclik
                _logger.info('\n\n\n Activate VARIANTE \n\n\n\n--->>  %s\n\n\n\n')
                response = requests.patch(str(domain) + str(url_activate_product) + "rc_" + str(self.id),
                                          headers=self.headers)

                _logger.info('\n\n\n(activate variante) response from eki \n\n\n\n--->  %s\n\n\n\n',
                             response.content)

        rec = super(EkiProduct, self).write(vals)

        return rec
