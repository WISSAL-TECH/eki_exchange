from odoo import models, fields, api
import logging
import json
import sys

import requests
# from minio import Minio
import re
from odoo import models, fields, api, exceptions
from odoo.http import request

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    create_by = fields.Char()

    def create(self, vals):
        if 'create_by' in vals and vals['create_by'] != 'odoo':
            logging.warning("create pos from ekiclik ======")
            logging.warning(vals)
            domain = ""
            domain_cpa = ""
            config_settings = self.env['res.config.settings'].search([], order='id desc', limit=1)
            if config_settings:
                domain = config_settings.domain
                domain_cpa = config_settings.domain_cpa
            url_pos = "/api/odoo/pos"

            data = {"name_pos": vals['name_pos'],
                    "address_pos":  vals['address_pos'],
                    "pos_phone_one": vals['pos_phone_one'],
                    "pos_phone_two": vals['pos_phone_two'],
                    "pos_wilaya": vals['pos_wilaya'],
                    "pos_commune": vals['pos_commune'],
                    "codification": vals['codification'],
                    "ek_user_emails": ["email1@example.com", "email2@example.com"],
                    "source": vals['source']}
            ek_user_emails = []

            for value in vals['ek_user_emails']:
                ek_user_emails.append(value)

            data["ek_user_emails"] = ek_user_emails

            if "source" in vals and vals['source']:
                if vals['source'] == 'salam':
                    # envoyer pdv a cpa
                    _logger.info(
                        '\n\n\n pos BODY JSON \n\n\n\n--->>  %s\n\n\n\n', data)
                    response_cpa = requests.post(str(domain_cpa) + str(url_pos), data=json.dumps(data),
                                                 headers=self.headers)
                    _logger.info('\n\n\n(CREATE pos) response from cpa\n\n\n\n--->  %s\n\n\n\n',
                                 response_cpa.content)
                elif vals['source'] == "cpa":
                    _logger.info(
                        '\n\n\n pos BODY JSON \n\n\n\n--->>  %s\n\n\n\n', data)
                    response = requests.post(str(domain) + str(url_pos), data=json.dumps(data),
                                             headers=self.headers)
                    _logger.info('\n\n\n(CREATE pos) response from alsalam \n\n\n\n--->  %s\n\n\n\n',
                                 response.content)

            rec = super(ResCompany, self).create({
                'name': vals.get('name_pos'),
                'codification': vals.get('codification'),
            })

            return rec
        else:
            logging.warning("create pos from odoo ======")
            logging.warning(vals)
            rec = super(ResCompany, self).create(vals)

            return rec
