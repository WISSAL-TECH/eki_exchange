from odoo import models, fields, api
import logging
import json
import sys

import requests
# from minio import Minio
import re
from odoo import models, fields, api, exceptions
from odoo.http import request
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EkWilaya(models.Model):
    _name = 'ek.wilaya'
    _rec_name = 'name'

    name = fields.Char("Wilaya")
class EkCommune(models.Model):
    _name = 'ek.commune'
    _rec_name = 'name'

    name = fields.Char("Commune")

class ResCompany(models.Model):
    _inherit = 'res.company'

    create_by = fields.Char()
    source = fields.Char()
    pos_commune = fields.Many2one("ek.commune", "Commune")
    pos_wilaya = fields.Many2one("ek.wilaya", "Wilaya")
    country_id = fields.Many2one('res.country', string='Country', required=True, default=lambda self: self._default_country())

    @api.model
    def _default_country(self):
        algeria = self.env['res.country'].search([('name', '=', 'Algérie')], limit=1)
        return algeria.id if algeria else False

    def _check_codification_length(self, vals):
        codification = vals.get('codification')
        if codification and len(codification) != 21:
            raise UserError("Codification must be 21 characters long.")

    headers = {"Content-Type": "application/json", "Accept": "application/json", "Catch-Control": "no-cache"}

    def write(self, vals):
        self._check_codification_length(vals)
        logging.warning("create pos ======")
        logging.warning(vals)
        domain = ""
        domain_cpa = ""
        config_settings = self.env['res.config.settings'].search([], order='id desc', limit=1)
        if config_settings:
            domain = config_settings.domain
            domain_cpa = config_settings.domain_cpa
        url_pos = "/api/odoo/pos"
        logging.warning("update pos from odoo ======")
        logging.warning(vals)
        if vals.get('pos') or self.pos:
            body = {"params": {"data": {}}}
            wilaya = self.state_id.name if self.state_id else ''
            commune = self.pos_commune.name if self.pos_commune else ''

            data = {
                "name_pos": vals.get('name', self.name),
                "address_pos": vals.get('street', self.street),
                "pos_phone_one": vals.get('phone', self.phone),
                "pos_phone_two": vals.get('mobile', self.mobile) if self.mobile else '',
                "pos_wilaya": wilaya,
                "pos_commune": commune,
                "codification": vals.get('codification', self.codification),
                "status": "ACTIVE",
                "source": vals.get('source', self.source)
            }

            ek_user_emails = []
            if vals.get("users"):
                users = self.env['res.users'].browse(vals['users'])
                ek_user_emails.extend([user.login for user in users if user.login])
            elif self.users:
                ek_user_emails.extend([user.login for user in self.users if user.login])

            if vals.get("pos_user"):
                pos_record = self.env['res.users'].browse(vals['pos_user'])
                ek_user_emails.extend([pos_record.login for pos_record in pos_record if pos_record.login])
            elif self.pos_user:
                ek_user_emails.append(self.pos_user.login)

            data["ek_user_emails"] = ek_user_emails
            body["params"]["data"] = data

            _logger.info('\n\n\n D A T A \n\n\n\n--->>  %s\n\n\n\n', body)

            response_cpa = requests.put(str(domain_cpa) + str(url_pos), data=json.dumps(body), headers=self.headers)
            _logger.info('\n\n\n(UPDATE POS) response from cpa\n\n\n\n--->  %s\n\n\n\n', response_cpa.content)

            response = requests.put(str(domain) + str(url_pos), data=json.dumps(body), headers=self.headers)
            _logger.info('\n\n\n(UPDATE POS) response from alsalam \n\n\n\n---> %s\n\n\n\n', response.content)

        return super(ResCompany, self).write(vals)


    @api.model
    def create(self, vals):
        self._check_codification_length(vals)

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
            rec = super(ResCompany, self).create(vals)

            if 'pos' in vals and vals['pos'] == True:
                body = {"params": {
                    "data": {
                    }
                }
                }
                wilaya = ""
                if 'state_id' in vals and vals['state_id']:
                    state = self.env['res.country.state'].search([('id', '=', vals['state_id'])], limit=1)
                    wilaya = state.name
                commune = ""
                if 'pos_commune' in vals and vals['pos_commune']:
                    state = self.env['ek.commune'].search([('id', '=', vals['pos_commune'])], limit=1)
                    commune = state.name
                data = {"name_pos": vals.get('name') if vals.get('name') else '',
                        "address_pos": vals.get('street') if vals.get('street') else '',
                        "pos_phone_one": vals.get('phone') if vals.get('phone') else '',
                        "pos_phone_two": vals.get('mobile') if vals.get('mobile') else '',
                        "pos_wilaya": wilaya if wilaya else self.state_id.name,
                        "pos_commune": commune if commune else self.pos_commune.name,
                        "codification": vals.get('codification') if vals.get('codification') else '',
                        "status": "ACTIVE",
                        "source": vals.get('source') if vals.get('source') else ''}
                ek_user_emails = []

                if "users" in vals:
                    users = self.env['res.users'].browse(vals['users'])
                    if users and users.login:
                        ek_user_emails.append(users.login)
                elif self.users and self.users.login:
                        ek_user_emails.append(self.users.login)

                if "pos_user" in vals:
                    pos_id = vals['pos_user']  # Get the ID of the 'pos' field from vals

                    pos_record = self.env['res.users'].browse(pos_id)

                    # Now you can access the login field of the 'pos' record
                    if pos_record and pos_record.login:
                        # If the 'pos' record exists and has a login value
                        ek_user_emails.append(pos_record.login)
                else:
                    pos_id = self.pos_user  # Get the ID of the 'pos' field from vals

                    pos_record = self.env['res.users'].browse(pos_id)

                    # Now you can access the login field of the 'pos' record
                    if pos_record and pos_record.login:
                        # If the 'pos' record exists and has a login value
                        ek_user_emails.append(pos_record.login)

                data["ek_user_emails"] = ek_user_emails
                body["params"]["data"] = data

                _logger.info('\n\n\n D A T A \n\n\n\n--->>  %s\n\n\n\n', body)

                response_cpa = requests.post(str(domain_cpa) + str(url_pos), data=json.dumps(body),
                                             headers=self.headers)
                _logger.info('\n\n\n(CREATE POS) response from cpa\n\n\n\n--->  %s\n\n\n\n', response_cpa.content)

                response = requests.post(str(domain) + str(url_pos), data=json.dumps(body),
                                         headers=self.headers)
                _logger.info('\n\n\n(CREATE POS) response from alsalam \n\n\n\n--->  %s\n\n\n\n', response.content)

                return rec

            else:
                rec = super(ResCompany, self).create(vals)

                return rec
