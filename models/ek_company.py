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


class EkWilaya(models.Model):
    _name = 'ek.wilaya'
    _rec_name = 'name'

    name = fields.Char("Wilaya")

class ResCompany(models.Model):
    _inherit = 'res.company'

    create_by = fields.Char()
    source = fields.Char()
    pos_commune = fields.Char("Commune")
    pos_wilaya = fields.Many2one("ek.wilaya", "Wilaya")


    headers = {"Content-Type": "application/json", "Accept": "application/json", "Catch-Control": "no-cache"}

    @api.model
    def create(self, vals):
        logging.warning("create pos ======")
        logging.warning(vals)
        domain = ""
        domain_cpa = ""
        config_settings = self.env['res.config.settings'].search([], order='id desc', limit=1)
        if config_settings:
            domain = config_settings.domain
            domain_cpa = config_settings.domain_cpa
        url_pos = "/api/odoo/pos"

        if 'create_by' in vals and vals.get('create_by') != 'odoo':
            logging.warning("create pos from ekiclik ======")
            logging.warning(vals)


            body = {"params": {
                "data": {
                }
            }
            }
            data = {"name_pos": vals.get('name_pos'),
                    "address_pos": vals.get('address_pos'),
                    "pos_phone_one": vals.get('pos_phone_one'),
                    "pos_phone_two": vals.get('pos_phone_two'),
                    "pos_wilaya": vals.get('pos_wilaya'),
                    "pos_commune": vals.get('pos_commune'),
                    "codification": vals.get('codification'),
                    "status": vals.get('status'),
                    "source": vals.get('source')}
            ek_user_emails = []

            if "ek_user_emails" in vals and vals['ek_user_emails']:
                for value in vals['ek_user_emails']:
                    ek_user_emails.append(value)

            data["ek_user_emails"] = ek_user_emails
            body["params"]["data"] = data
            _logger.info(
                '\n\n\n D A T A \n\n\n\n--->>  %s\n\n\n\n', body)
            if "source" in vals and vals.get('source'):
                if vals['source'] == 'salam':
                    # envoyer pdv a cpa
                    _logger.info(
                        '\n\n\n pos BODY JSON \n\n\n\n--->>  %s\n\n\n\n', body)
                    response_cpa = requests.post(str(domain_cpa) + str(url_pos), data=json.dumps(body),
                                                 headers=self.headers)
                    _logger.info('\n\n\n(CREATE pos) response from cpa\n\n\n\n--->  %s\n\n\n\n',
                                 response_cpa.content)
                elif vals['source'] == "cpa":
                    _logger.info(
                        '\n\n\n pos BODY JSON \n\n\n\n--->>  %s\n\n\n\n', body)
                    response = requests.post(str(domain) + str(url_pos), data=json.dumps(body),
                                             headers=self.headers)
                    _logger.info('\n\n\n(CREATE pos) response from alsalam \n\n\n\n--->  %s\n\n\n\n',
                                 response.content)
            vals.pop("ek_user_emails")
            vals.pop("source")
            vals.pop("pos_commune")
            vals.pop("pos_wilaya")
            vals.pop("status")
            vals["name"] = vals.get('name_pos')
            vals.pop("name_pos")
            logging.warning("create pos from ek ======")
            logging.warning(vals)
            rec = super(ResCompany, self).create(vals)

            return rec
        else:
            logging.warning("create pos from odoo ======")
            logging.warning(vals)
            if vals.get('pos')== True:

                data = {"name_pos": vals.get('name') if vals.get('name') else '',
                        "address_pos": vals.get('login') if vals.get('login') else '',
                        "pos_phone_one": vals.get('phone') if vals.get('phone') else '',
                        "pos_phone_two": vals.get('mobile') if vals.get('mobile') else '',
                        "pos_wilaya": vals.get('pos_wilaya') if vals.get('pos_wilaya') else '',
                        "pos_commune": vals.get('pos_commune') if vals.get('pos_commune') else '',
                        "codification": vals.get('codification') if vals.get('codification') else '',
                        "status": "ACTIVE",
                        "source": vals.get('source') if vals.get('source') else ''}
                ek_user_emails = []

                if "users" in vals and isinstance(vals['users'], list):
                    users = self.env['res.users'].browse(vals['users'])
                    for user in users:
                        ek_user_emails.append(user.login)

                data["ek_user_emails"] = ek_user_emails
                _logger.info('\n\n\n D A T A \n\n\n\n--->>  %s\n\n\n\n', data)

                response_cpa = requests.post(str(domain_cpa) + str(url_pos), data=json.dumps(data),
                                             headers=self.headers)
                _logger.info('\n\n\n(CREATE POS) response from cpa\n\n\n\n--->  %s\n\n\n\n', response_cpa.content)

                response = requests.post(str(domain) + str(url_pos), data=json.dumps(data),
                                         headers=self.headers)
                _logger.info('\n\n\n(CREATE POS) response from alsalam \n\n\n\n--->  %s\n\n\n\n', response.content)
                rec = super(ResCompany, self).create(vals)

                return rec

            else:
                rec = super(ResCompany, self).create(vals)

                return rec
