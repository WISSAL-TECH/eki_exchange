import json
import sys

import boto3
import requests
# from minio import Minio
import re
from odoo import models, fields, api, exceptions, _
from odoo.http import request
import logging
from _datetime import datetime
from odoo.exceptions import ValidationError

from urllib.parse import quote
from io import BytesIO, StringIO
from .config import *
import base64
import random
import string

_logger = logging.getLogger(__name__)


class Product(models.Model):
    _inherit = ['product.template']

    create_by = fields.Char(string="Créé à partir de", readonly=True)
    brand = fields.Many2one("product.brand", 'Marque')
    image_url = fields.Char(string='Image URL')
    manufacture_name = fields.Char(string='Fabricant')
    certificate = fields.Binary("Certificat")
    certificate_url = fields.Char("Certificate URL")
    ref_odoo = fields.Char("ref odoo")

    constructor_ref = fields.Char("Réference constructeur",
                                  required=True
                                  #default="Merci de Générer/entrer une référence constructeur",
                                  )
    brand_id = fields.Many2one("product.brand", string="Marque")
    default_code = fields.Char(string="Reference interne", invisible=True)
    company_id = fields.Many2one("res.company", string="Société", invisible=True)
    categ_id = fields.Many2one("product.category", string="Catégorie d'article", required=True)
    attribute_line_ids = fields.One2many('product.template.attribute.line', 'product_tmpl_id', 'Product Attributes',
                                         copy=True, required=True)
    detailed_type = fields.Selection([
        ('consu', 'Consommable'),
        ('service', 'Service'), ('product', 'Article stockable')], string="Type d'article", default='product',
        required=True,
        help=
        "Un produit stockable est un produit dont on gère le stock. L'application \"Inventaire\" doit être installée. \n"
        "Un produit consommable, d'un autre côté, est un produit pour lequel le stock n'est pas géré.\n"
        "Un service est un produit immatériel que vous fournissez.")

    prix_central = fields.Float("Prix centrale des achats", compute='_compute_prices', readonly=False, store=True)
    prix_ek = fields.Float("Prix ekiclik", compute='_compute_prices', readonly=False, store=True)
    price = fields.Float("Prix PDVA", compute='_compute_prices', readonly=False, store=True)

    @api.depends('standard_price', 'categ_id', 'price')
    def _compute_prices(self):
        """ Compute the value of prix_ek prix_centrale  """
        _logger.info('\n\n\n onchange cout PRODUCT \n\n\n\n--->> \n\n\n\n')
        for record in self:
            price = record.standard_price
            marge2 = 1.5  # default margin is 50%

            # Check if the product category is 'MEUBLE'
            if (record.categ_id and ('MEUBLES' in record.categ_id.name or
                                     (record.categ_id.parent_id and 'MEUBLES' in record.categ_id.parent_id.name) or
                                     (record.categ_id.parent_id and record.categ_id.parent_id.parent_id and
                                      'MEUBLES' in record.categ_id.parent_id.parent_id.name))):
                marge2 = 1.6
            if record.price:
                _logger.info('\n\n\n onchange cout PRODUCT priiice \n\n\n\n--->> \n\n\n\n')

                record.prix_ek = round(record.price * marge2, 2)
            else:
                marge1 = (record.standard_price * 11.11) / 100
                prix_central = round(price + marge1, 2)
                record.prix_central = prix_central
                _logger.info('\n\n\n onchange cout PRODUCT CENTRALE DEES ACHATS \n\n\n\n--->> \n\n\n\n')

                record.prix_ek = round(prix_central * marge2, 2)



    def generate_unique_reference(self):
        # Generate 5 random letters
        letters = ''.join(random.choices(string.ascii_uppercase, k=5))

        # Generate 5 random numbers
        numbers = ''.join(random.choices(string.digits, k=5))

        # Combine letters and numbers to create the reference
        new_reference = letters + numbers

        return new_reference

    def action_generate_reference(self):
        for record in self:
            new_reference = record.generate_unique_reference()
            record.constructor_ref = new_reference

    @api.constrains('attribute_line_ids')
    def _check_attribute_line_ids(self):
        for record in self:
            if not record.attribute_line_ids:
                raise ValidationError(
                    _("Dans l'onglet Attributs et variantes veuillez sélectionner au moins une variante."))

    def generate_name_variante(self, name, ref):
        """Generating name for ek products"""
        _logger.info('\n\n\n GENERATING NAME\n\n\n\n--->  %s\n\n\n\n', name)
        # Add default code if exists

        if ref:
            name += ' ' + ref
            _logger.info('\n\n\n GENERATING NAME\n\n\n\n--->  %s\n\n\n\n', name)

        _logger.info('\n\n\n GENERATING NAME\n\n\n\n--->  %s\n\n\n\n', name)

        return name

    def create_doc_url(self, attach):
        s3 = boto3.client('s3',
                          aws_access_key_id='AKIAXOFYUBQFSP2WOT5R',
                          aws_secret_access_key='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',
                          region_name='eu-west-2'
                          )
        bucket = "wicommerce-storage"
        if attach.datas:
            # Generate a unique S3 key for the image
            s3_key = f'attachments/{attach.res_id}{attach.name}'
            s3_key_encoded = quote(s3_key)
            # Convert the image binary data to a BytesIO object
            data_fileobj = BytesIO(base64.standard_b64decode(attach.datas))

            # Upload the image to S3
            s3.put_object(Bucket=bucket, Key=s3_key, Body=data_fileobj, ContentType=attach.mimetype)

            # Construct the S3 image URL
            s3_url = f'https://{bucket}.s3.eu-west-2.amazonaws.com/{s3_key_encoded}'

            # Update the product record with the S3 image URL
            return s3_url

    def _compute_certificate_url(self, certificat):
        for record in self:
                # Extract the binary data from the 'certificate' field
                certificate_data = record.certificate

                # Create an attachment record
                attachment = self.env['ir.attachment'].create({
                    'name': 'Certificate Attachment',  # Set the name of the attachment as desired
                    'datas': certificate_data,
                    'res_model': self._name,
                    'res_id': record.id,
                })

                # Obtain the URL of the attachment
                certificate_url = record.create_doc_url(attachment)

                # Update the 'certificate_url' field with the URL
                record.certificate_url = certificate_url

    def _compute_certificate(self):
        for record in self:
            url = record.certificate_url
            response = requests.get(url)
            if response.status_code == 200:
                # Store PDF binary content in the binary field
                record.certificate = base64.b64encode(response.content)

    # set the url and headers
    headers = {"Content-Type": "application/json", "Accept": "application/json", "Catch-Control": "no-cache"}

    @api.model
    def create(self, vals):
        logging.warning("create product ======")
        logging.warning(vals)

        # 1- CREATE A PRODUCT FROM ekiclik
        domain = "https://apiadmin-alsalam.ekiclik.dz"
        domain_cpa = "https://apiadmin-cpa.ekiclik.dz"
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
            elif 'category' in vals and vals['category'] is None:
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
            random_number = random.randint(100000, 999999)
            vals["ref_odoo"] = "rc_" + str(random_number)

            rec = super(Product, self).create(vals)


            if 'tax_string' in vals and vals.get('tax_string'):
                pattern = r'(\d[\d\s,.]+)'

                # Use the findall function to extract all matches
                matches = re.findall(pattern, vals.get('tax_string'))

                # Join the matches into a single string (if there are multiple matches)
                numeric_value = ''.join(matches)

                # Replace commas with dots (if necessary)
                numeric_value = numeric_value.replace(',', '.')

                # Remove non-breaking space characters
                numeric_value = numeric_value.replace('\xa0', '')
            elif rec.tax_string:
                pattern = r'(\d[\d\s,.]+)'

                # Use the findall function to extract all matches
                matches = re.findall(pattern, rec.tax_string)

                # Join the matches into a single string (if there are multiple matches)
                numeric_value = ''.join(matches)

                # Replace commas with dots (if necessary)
                numeric_value = numeric_value.replace(',', '.')

                # Remove non-breaking space characters
                numeric_value = numeric_value.replace('\xa0', '')
            elif self.tax_string:
                pattern = r'(\d[\d\s,.]+)'

                # Use the findall function to extract all matches
                matches = re.findall(pattern, self.tax_string)

                # Join the matches into a single string (if there are multiple matches)
                numeric_value = ''.join(matches)

                # Replace commas with dots (if necessary)
                numeric_value = numeric_value.replace(',', '.')

                # Remove non-breaking space characters
                numeric_value = numeric_value.replace('\xa0', '')

            else:
                numeric_value = vals['list_price'] if vals['list_price'] else rec.list_price

            _logger.info('\n\n\n(CREATE product) numeric_value \n\n\n\n--->  %s\n\n\n\n',
                         numeric_value)
            product_json = {
                "name": rec.name,
                "description": rec.description,
                "categoryName": rec.categ_id.name,
                "brand": {
                    "name": rec.brand_id.name,
                    "reference": "br_" + str(rec.brand_id.id)
                },
                "refConstructor": rec.constructor_ref if rec.constructor_ref else "null",
                "manufactureName": rec.manufacture_name if rec.constructor_ref else '',
                "activate": True,
                "ref_odoo": rec.ref_odoo,

            }
            variantes = self.env['product.product'].search([('product_tmpl_id', '=', rec.id)])
            configurations = []
            cout = rec.standard_price
            if variantes:
                for record in variantes:
                    _logger.info(
                        '\n\n\n update cout on variante\n\n\n\n--->>  %s\n\n\n\n', cout)
                    record.write({'standard_price': cout})

                    if record.product_template_attribute_value_ids:
                        values = []
                        for value in record.product_template_attribute_value_ids:
                            values.append(value.name)
                        # generate reference for variante
                        reference = record.generate_code()
                        record.write({'reference': reference})
                        # take reference value
                        reference = record.reference if record.reference else rec.constructor_ref

                        # generate name for variante

                        name = record.generate_name_variante(rec.name, rec.constructor_ref,
                                                             values)
                        if self.company_id.name == "Centrale des Achats":
                            price = record.prix_central
                        else:
                            price = record.price

                        configuration = {
                            'name': name,
                            "description": '',
                            "reference": record.reference if record.reference else rec.constructor_ref,
                            "price": record.prix_ek,
                            "buyingPrice": record.prix_central,
                            "productCharacteristics": [],
                            "images": rec.image_url if rec.image_url else 'image_url',
                            "active": True if rec.image_url else False,
                            "certificateUrl": record.certificate_url,
                            "ref_odoo": record.ref_odoo,
                        }

                        for value in record.product_template_attribute_value_ids:
                            product_characteristic = {
                                "name": value.attribute_id.name if value.attribute_id else '',
                                "value": value.product_attribute_value_id.name if value.product_attribute_value_id else ''
                            }
                            configuration["productCharacteristics"].append(product_characteristic)
                        configurations.append(configuration)
                    else:
                        name = rec.generate_name_variante(rec.name, rec.constructor_ref)

                        configuration = {
                            'name': rec.name,
                            "description": '',
                            "reference": rec.constructor_ref,
                            "price": rec.prix_ek,
                            "buyingPrice": rec.standard_price,
                            "productCharacteristics": [],
                            "images": rec.image_url if rec.image_url else 'image_url',
                            "active": True if rec.image_url else False,
                            "certificateUrl": rec.certificate_url,
                            "ref_odoo": record.ref_odoo,
                        }

                        configuration["productCharacteristics"].append({"name": "couleur", "value": None})

                        configurations.append(configuration)

            product_json["configurations"] = configurations

            _logger.info(
                '\n\n\n PRODUCT BODY JSON\n\n\n\n--->>  %s\n\n\n\n', product_json)
            response = requests.post(str(domain) + str(url_product), data=json.dumps(product_json),
                                     headers=self.headers)
            _logger.info('\n\n\n(CREATE product) response from eki \n\n\n\n--->  %s\n\n\n\n',
                         response.content)
            response_cpa = requests.post(str(domain_cpa) + str(url_product), data=json.dumps(product_json),
                                         headers=self.headers)
            _logger.info('\n\n\n(CREATE product) response from eki cpa \n\n\n\n--->  %s\n\n\n\n',
                         response_cpa.content)

            return rec

    # def create_doc_url(self, attach):
    # client = Minio("play.min.io",
    #               access_key="admin",
    #               secret_key="d%gHsjnZ*eD")
    # bucket_name = "file-storage-document-salam"
    # destination_file = "eki_file"+str(attach.id)

    # if attach.datas:
    #    data_fileobj = BytesIO(base64.standard_b64decode(attach.datas))

    #    client.fput_object(
    #       bucket_name, destination_file, data_fileobj,
    #    )

    # Get the URL for the uploaded file
    #    url = client.presigned_get_object(bucket_name, destination_file)

    #    print(
    #        data_fileobj, "successfully uploaded as object",
    #        destination_file, "to bucket", bucket_name,
    #    )

    #    attach.write({'url': url})

    def write(self, vals):
        domain = "https://apiadmin-alsalam.ekiclik.dz"
        domain_cpa = "https://apiadmin-cpa.ekiclik.dz"
        config_settings = self.env['res.config.settings'].search([], order='id desc', limit=1)

        _logger.info(
            '\n\n\nDOMAAIN\n\n\n\n--->>  %s\n\n\n\n', domain)
        url_archive_product = "/api/odoo/products/archive/"
        url_activate_product = "/api/odoo/products/activate/"
        url_update_product = "/api/odoo/products/update"

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
            pattern = r'(\d[\d\s,.]+)'

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


            brand_name = self.brand_id.name if self.brand_id else ''
            if "brand_id" in vals:
                brand = self.env['product.brand'].search([('id', '=', vals['brand_id'])])
                brand_name = brand.name if brand else self.brand_id.name

            categ_name = self.categ_id.name
            if "categ_id" in vals:
                categ = self.env['product.category'].search([('id', '=', vals['categ_id'])])
                categ_name = categ.name if categ else self.brand_id.name
            fab = self.manufacture_name if self.manufacture_name else ''
            # sending update to ekiclik
            data = {
                "name": vals.get("name", "") if vals.get("name") else self.name,
                "description": vals.get("description", "") if vals.get("description") else "",
                "categoryName": categ_name,
                "brand": {
                    "name": brand_name,
                    "reference": vals.get("brand_id", "") if vals.get("brand_id") else ""
                },
                "refConstructor": vals.get("constructor_ref", "") if vals.get(
                    "constructor_ref") else self.constructor_ref,
                "manufactureName": vals.get("manufacture_name", "") if vals.get(
                    "manufacture_name") else fab,
                "activate": True,
                # "oldRef": vals.get("constructor_ref", "") if vals.get("constructor_ref") else "",
                "ref_odoo": vals.get("ref_odoo", "") if vals.get(
                    "ref_odoo") else self.ref_odoo,
            }

            _logger.info('\n\n\n UPDATE PRODUCT \n\n\n\n--->>  %s\n\n\n\n', data)
            response = requests.put(str(domain) + str(url_update_product), data=json.dumps(data),
                                    headers=self.headers)
            _logger.info('\n\n\n(update product) response from eki \n\n\n\n--->  %s\n\n\n\n',
                         response.content)
            response_cpa = requests.put(str(domain_cpa) + str(url_update_product), data=json.dumps(data),
                                        headers=self.headers)
            _logger.info('\n\n\n(update product) response from eki  CPA\n\n\n\n--->  %s\n\n\n\n',
                         response_cpa.content)

            if "active" in vals and vals["active"] == False:
                # send archive product to ekiclik
                _logger.info('\n\n\n Archive PRODUCT \n\n\n\n--->>  %s\n\n\n\n')
                response = requests.patch(str(domain) + str(url_archive_product) + str(self.ref_odoo),
                                          headers=self.headers)

                _logger.info('\n\n\n(archive product) response from eki \n\n\n\n--->  %s\n\n\n\n',
                             response.content)
                response_cpa = requests.patch(str(domain_cpa) + str(url_archive_product) + str(self.ref_odoo),
                                              headers=self.headers)

                _logger.info('\n\n\n(archive product) response from eki CPA\n\n\n\n--->  %s\n\n\n\n',
                             response_cpa.content)
            elif "active" in vals and vals["active"] == True:
                # send activate product to ekiclik
                _logger.info('\n\n\n Activate PRODUCT \n\n\n\n--->>  %s\n\n\n\n')
                response = requests.patch(str(domain) + str(url_activate_product) + "rc_" + str(self.id),
                                          headers=self.headers)

                _logger.info('\n\n\n(activate product) response from eki \n\n\n\n--->  %s\n\n\n\n',
                             response.content)
                response_cpa = requests.patch(str(domain_cpa) + str(url_activate_product) + "rc_" + str(self.id),
                                              headers=self.headers)

                _logger.info('\n\n\n(activate product) response from eki cpa\n\n\n\n--->  %s\n\n\n\n',
                             response_cpa.content)

            return rec


class EkiProduct(models.Model):
    _inherit = ['product.product']

    headers = {"Content-Type": "application/json", "Accept": "application/json", "Catch-Control": "no-cache"}
    manufacture_name = fields.Char(string='Fabricant')
    reference = fields.Char(string='Réference')
    ref_odoo = fields.Char("ref odoo")
    barcode = fields.Char("Code-barres", readonly=True)
    certificate = fields.Binary("Certificat")
    certificate_url = fields.Char("Certificate URL")
    image_url = fields.Char()
    image_count = fields.Float()
    name_store = fields.Char("name")
    prix_central = fields.Float("Prix centrale des achats", compute='_compute_prices', readonly=False, store=True)
    prix_ek = fields.Float("Prix ekiclik", compute='_compute_prices', readonly=False, store=True)
    constructor_ref = fields.Char(
        string='Réference constructeur produit',
        compute='_compute_constructor_ref',
        store=True
    )
    price = fields.Float(string='Prix pdva', company_dependent=True, compute='_compute_prices', store=True)

    def create_purchase_order(self, partner_name='Centrale des achats'):
        # Search for the partner by name
        partners = self.env['res.partner'].name_search(name=partner_name, limit=1)
        if not partners:
            raise ValueError(f"The partner '{partner_name}' does not exist.")

        partner_id = partners[0][0]  # Extract the partner ID from the search result

        order_lines = []

        # Iterate over the selected products
        for product in self:
            if not product:
                raise ValueError("Product does not exist.")

            # Use the virtual_quantity as the quantity to order
            product_qty = product.virtual_available  # virtual_available provides the virtual quantity

            order_line = {
                'product_id': product.id,
                'product_qty': product_qty,
                'product_uom': product.uom_id.id,
                'price_unit': product.standard_price,
                'name': product.name,
            }
            order_lines.append((0, 0, order_line))

        # Create the purchase order
        purchase_order = self.env['purchase.order'].create({
            'partner_id': partner_id,
            'order_line': order_lines,
        })

        return purchase_order

    def _compute_constructor_ref(self):
        for product in self:
            product.constructor_ref = product.product_tmpl_id.constructor_ref

    @api.depends('standard_price', 'categ_id', 'price')
    def _compute_prices(self):
        """ Compute the value of prix_ek prix_centrale  """
        _logger.info('\n\n\n onchange cout PRODUCT \n\n\n\n--->> \n\n\n\n')
        for record in self:
            price = record.standard_price
            marge2 = 1.5  # default margin is 50%

            # Check if the product category is 'MEUBLE'
            if (record.categ_id and ('MEUBLES' in record.categ_id.name or
                                     (record.categ_id.parent_id and 'MEUBLES' in record.categ_id.parent_id.name) or
                                     (record.categ_id.parent_id and record.categ_id.parent_id.parent_id and
                                      'MEUBLES' in record.categ_id.parent_id.parent_id.name))):
                marge2 = 1.6
            if record.price:
                _logger.info('\n\n\n onchange cout PRODUCT priiice \n\n\n\n--->> \n\n\n\n')

                record.prix_ek = round(record.price * marge2, 2)
            else:
                marge1 = (record.standard_price * 11.11) / 100
                prix_central = round(price + marge1, 2)
                record.prix_central = prix_central
                _logger.info('\n\n\n onchange cout PRODUCT CENTRALE DEES ACHATS \n\n\n\n--->> \n\n\n\n')

                record.prix_ek = round(prix_central * marge2, 2)


    def create_doc_url(self, attach):
        s3 = boto3.client('s3',
                          aws_access_key_id='AKIAXOFYUBQFSP2WOT5R',
                          aws_secret_access_key='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',
                          region_name='eu-west-2'
                          )
        bucket = "wicommerce-storage"
        if attach.datas:
            # Generate a unique S3 key for the image
            s3_key = f'attachments/{attach.res_id}{attach.name}'
            s3_key_encoded = quote(s3_key)
            # Convert the image binary data to a BytesIO object
            data_fileobj = BytesIO(base64.standard_b64decode(attach.datas))

            # Upload the image to S3
            s3.put_object(Bucket=bucket, Key=s3_key, Body=data_fileobj, ContentType=attach.mimetype)

            # Construct the S3 image URL
            s3_url = f'https://{bucket}.s3.eu-west-2.amazonaws.com/{s3_key_encoded}'

            # Update the product record with the S3 image URL
            return s3_url

    def generate_code(self):
        """Generating default code for ek products"""

        # Generate a random 6-digit number
        random_number = random.randint(100000, 999999)

        # Concatenate the "eki_" and random number
        product_code = f"eki_{random_number}"

        return product_code

    def generate_name_variante(self, name, ref, variante):
        """Generating name for ek products"""
        _logger.info('\n\n\n GENERATING NAME\n\n\n\n--->  %s\n\n\n\n', name)
        # Add default code if exists

        if ref:
            name += ' ' + ref
            _logger.info('\n\n\n GENERATING NAME\n\n\n\n--->  %s\n\n\n\n', name)
        if variante:
            for v in variante:
                name += ' ' + str(v)
            _logger.info('\n\n\n GENERATING NAME\n\n\n\n--->  %s\n\n\n\n', name)

        _logger.info('\n\n\n GENERATING NAME\n\n\n\n--->  %s\n\n\n\n', name)

        return name

    def generate_name(self, vals):
        """Generating name for ek products"""
        _logger.info('\n\n\n GENERATING NAME\n\n\n\n--->  %s\n\n\n\n')
        # _logger.info('\n\n\n vals NAME\n\n\n\n--->  %s\n\n\n\n',vals["name"])
        # _logger.info('\n\n\n self NAME\n\n\n\n--->  %s\n\n\n\n',self.name)
        name = ''
        if "name" in vals and vals['name'] or self.name:
            name = vals['name'] if "name" in vals and vals['name'] else self.name

        # Iterate through each record in the Many2Many field
        for variant_value in self.product_template_variant_value_ids:
            name += ' ' + str(variant_value.name)
            _logger.info('\n\n\n  NAME with variantes\n\n\n\n--->  %s\n\n\n\n', name)

        # Add brand name if exists
        # name += ' ' + str(self.brand_id.name) if self.brand_id else ''

        # Add default code if exists
        if "reference" in vals and vals["reference"]:
            name += ' ' + vals["reference"]
            _logger.info('\n\n\n GENERATING NAME\n\n\n\n--->  %s\n\n\n\n', name)

        elif self.reference:
            name += ' ' + str(self.reference)
            _logger.info('\n\n\n GENERATING NAME\n\n\n\n--->  %s\n\n\n\n', name)

        _logger.info('\n\n\n GENERATING NAME\n\n\n\n--->  %s\n\n\n\n', name)

        return name

    @api.model
    def create(self, vals):
        # Appeler la méthode de création de la classe parente
        random_number = random.randint(100000, 999999)
        vals["ref_odoo"] = "rc_variante" + str(random_number)
        _logger.info('\n\n\n creating variante vals\n\n\n\n--->  %s\n\n\n\n', vals)
        rec = super(EkiProduct, self).create(vals)
        return rec

    def write(self, vals):
        domain = "https://apiadmin-alsalam.ekiclik.dz"
        domain_cpa = "https://apiadmin-cpa.ekiclik.dz"
        config_settings = self.env['res.config.settings'].search([], order='id desc', limit=1)

        _logger.info('\n\n\nDOMAIN\n\n\n\n--->>  %s\n\n\n\n', domain)
        _logger.info('\n\n\nDOMAIN\n\n\n\n--->>  %s\n\n\n\n', domain_cpa)
        url_archive_product = "/api/odoo/products/configuration/archive/"
        url_activate_product = "/api/odoo/products/configuration/activate/"
        url_update_product = "/api/odoo/products/configuration"

        _logger.info('\n\n\n update\n\n\n\n--->>  %s\n\n\n\n', vals)

        for rec in self:
            origin_product = rec.product_tmpl_id
            # if not name :
            # name = origin_product.name
            # _logger.info('N A M E from product %s', name)
            numeric_value = 0
            if rec.tax_string:
                pattern = r'(\d[\d\s,.]+)'

                # Use the findall function to extract all matches
                matches = re.findall(pattern, rec.tax_string)

                # Join the matches into a single string (if there are multiple matches)
                numeric_value = ''.join(matches)

                # Replace commas with dots (if necessary)
                numeric_value = numeric_value.replace(',', '.')

                # Remove non-breaking space characters
                numeric_value = numeric_value.replace('\xa0', '')
            elif 'tax_string' in vals and vals['tax_string']:
                pattern = r'(\d[\d\s,.]+)'

                # Use the findall function to extract all matches
                matches = re.findall(pattern, vals['tax_string'])

                # Join the matches into a single string (if there are multiple matches)
                numeric_value = ''.join(matches)

                # Replace commas with dots (if necessary)
                numeric_value = numeric_value.replace(',', '.')

                # Remove non-breaking space characters
                numeric_value = numeric_value.replace('\xa0', '')
            else:
                numeric_value = vals['lst_price']
            if 'certificate_url' in vals:
                url = vals['certificate_url']
                response = requests.get(url)
                if response.status_code == 200:
                    # Store PDF binary content in the binary field
                    vals['certificate'] = base64.b64encode(response.content)
                _logger.info('\n\n\n giving value to certificate from certificate_url\n\n\n\n')

            if 'certificate' in vals and 'certificate_url' not in vals:
                # Extract the binary data from the 'certificate' field
                certificate_data = vals['certificate']

                # Create an attachment record
                attachment = self.env['ir.attachment'].create({
                    'name': 'Certificate Attachment',  # Set the name of the attachment as desired
                    'datas': certificate_data,
                    'res_model': self._name,
                    'res_id': rec.id,
                })

                # Obtain the URL of the attachment
                certificate_url = rec.create_doc_url(attachment)

                # Update the 'certificate_url' field with the URL
                vals['certificate_url'] = certificate_url

            if 'image_1920' in vals:
                if vals['image_1920']:
                    s3 = boto3.client('s3',
                                      aws_access_key_id='AKIAXOFYUBQFZJ5ZKR6B',
                                      aws_secret_access_key='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',
                                      region_name='eu-west-2'
                                      )
                    bucket = "imtech-product"
                    # Get the binary data from the binary field
                    image_data = vals['image_1920']

                    # Ensure image_data is in bytes format
                    if isinstance(image_data, str):
                        image_data = image_data.encode()

                    # Convert the image binary data to a BytesIO object
                    image_fileobj = BytesIO(image_data)

                    # Continue with the rest of the code
                    logging.warning('self')

                    # Generate a unique S3 key for the image
                    s3_key = f'product_images/{self.id}_{hash(self.name)}{self.image_count}.jpg'[:1024]
                    s3_key_encoded = quote(s3_key)

                    # Upload the image to S3
                    s3.put_object(Bucket=bucket, Key=s3_key, Body=image_fileobj, ContentType="image/jpg")

                    # Construct the S3 image URL
                    s3_url = f'https://{bucket}.s3.eu-west-2.amazonaws.com/{s3_key_encoded}'

                    # Update the product record with the S3 image URL
                    self.with_context(no_send_data=True).write({'image_url': s3_url})
                    self.image_count += 1

            no_image_image = rec.image_url if rec.image_url else ""
            no_certificate_url = rec.certificate_url if rec.certificate_url else ""
            values = []
            for value in rec.product_template_attribute_value_ids:
                values.append(value.name)

            # Check if 'name' key exists in vals, if not, use rec.name
            name = vals.get('name', rec.name)

            # Check if 'reference' key exists in vals, if not, use rec.reference
            reference = vals.get('reference', rec.reference)

            product = self.env['product.template'].search([('name', '=', name)], limit=1)

            # Generate name for product variant using rec.name, rec.reference, and values
            name = rec.generate_name_variante(name, product.constructor_ref, values)
            if self.company_id.name == "Centrale des Achats" or self.env.company.name == "Centrale des Achats":
                price = vals["prix_central"] if "prix_central" in vals else rec.prix_central
            else:
                price =vals["price"] if "price" in vals else rec.price


            data = {
                "name": vals["name"] if "name" in vals else rec.name,
                "reference": vals["reference"] if "reference" in vals else rec.reference,
                "product_ref_odoo": origin_product.ref_odoo if origin_product else "",
                "price": vals["prix_ek"] if "prix_ek" in vals else rec.prix_ek,
                "buyingPrice": vals["prix_central"] if "prix_central" in vals else rec.prix_central,
                "state": '',
                "productCharacteristics": [],
                "active": True if 'image_url' in vals else False,
                "description": vals["description"] if "description" in vals else rec.description,
                "certificateUrl": vals['certificate_url'] if 'certificate_url' in vals else no_certificate_url,
                "images": vals['image_url'] if 'image_url' in vals else no_image_image,
                # "oldRef": vals["reference"] if "reference" in vals else "",
                "ref_odoo": rec.ref_odoo
            }
            for value in rec.product_template_attribute_value_ids:
                product_characteristic = {
                    "name": value.attribute_id.name if value.attribute_id else '',
                    "value": value.product_attribute_value_id.name if value.product_attribute_value_id else ''
                }
                data["productCharacteristics"].append(product_characteristic)

            _logger.info('\n\n\n UPDATE VARIANTE \n\n\n\n--->>  %s\n\n\n\n', data)
            response = requests.put(str(domain) + str(url_update_product), data=json.dumps(data),
                                    headers=self.headers)

            _logger.info('\n\n\n(update variante) response from eki \n\n\n\n--->  %s\n\n\n\n',
                         response.content)
            response_cpa = requests.put(str(domain_cpa) + str(url_update_product), data=json.dumps(data),
                                        headers=self.headers)

            _logger.info('\n\n\n(update variante) response from eki cpa \n\n\n\n--->  %s\n\n\n\n',
                         response_cpa.content)
            if "active" in vals and vals["active"] == False:
                # send archive product to ekiclik
                _logger.info('\n\n\n Archive VARIANT \n\n\n\n--->>  %s\n\n\n\n')
                response = requests.patch(str(domain) + str(url_archive_product) + str(rec.ref_odoo),
                                          headers=self.headers)

                _logger.info('\n\n\n(archive variant) response from eki \n\n\n\n--->  %s\n\n\n\n',
                             response.content)
                response_cpa = requests.patch(str(domain_cpa) + str(url_archive_product) + str(rec.ref_odoo),
                                              headers=self.headers)

                _logger.info('\n\n\n(archive variant) response from eki  cpa\n\n\n\n--->  %s\n\n\n\n',
                             response_cpa.content)
            if "active" in vals and vals["active"] == True:
                # send activate product to ekiclik
                _logger.info('\n\n\n Activate VARIANT \n\n\n\n--->>  %s\n\n\n\n')
                response = requests.patch(str(domain) + str(url_activate_product) + str(rec.ref_odoo),
                                          headers=self.headers)

                _logger.info('\n\n\n(activate variant) response from eki \n\n\n\n--->  %s\n\n\n\n',
                             response.content)
                response_cpa = requests.patch(str(domain_cpa) + str(url_activate_product) + str(rec.ref_odoo),
                                              headers=self.headers)

                _logger.info('\n\n\n(activate variant) response from eki cpa \n\n\n\n--->  %s\n\n\n\n',
                             response_cpa.content)

        return super(EkiProduct, self).write(vals)