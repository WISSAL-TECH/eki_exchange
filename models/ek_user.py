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


class ResUsers(models.Model):
    _inherit = 'res.users'

    ek_user = fields.Boolean(string="Utilisateur ekiclik", default=False)
    first_name = fields.Char("Nom")
    last_name = fields.Char("Prénom")
    phone = fields.Char("Téléphone")
    address = fields.Char("Address")
    codification = fields.Char("Codification")
    roles = fields.Selection([
        ('ROLE_CREDIT_ANALYST_EK', 'Credit analyst'),
        ('ROLE_POS_EK', 'Role pos')
    ], )

    headers = {"Content-Type": "application/json", "Accept": "application/json", "Catch-Control": "no-cache"}

    @api.model
    def create(self, vals):
        rec = super(ResUsers, self).create(vals)

        logging.warning("create user ======")
        logging.warning(vals)

        domain = ""
        domain_cpa = ""
        config_settings = self.env['res.config.settings'].search([], order='id desc', limit=1)
        if config_settings:
            domain = config_settings.domain
            domain_cpa = config_settings.domain_cpa
            url_users = "/api/odoo/users"

        data = {
            "username": vals.get('name'),
            "first_name": vals.get('first_name'),
            "last_name": vals.get('last_name'),
            "phone": vals.get('phone'),
            "addresse": vals.get('addresse'),
            "codification": vals.get('codification'),
            "roles": vals.get('roles')
        }

        _logger.info('\n\n\n D A T A \n\n\n\n--->>  %s\n\n\n\n', data)

        response_cpa = requests.post(str(domain_cpa) + str(url_users), data=json.dumps(data),
                                     headers=self.headers)
        _logger.info('\n\n\n(CREATE user) response from cpa\n\n\n\n--->  %s\n\n\n\n', response_cpa.content)

        response = requests.post(str(domain) + str(url_users), data=json.dumps(data),
                                 headers=self.headers)
        _logger.info('\n\n\n(CREATE user) response from alsalam \n\n\n\n--->  %s\n\n\n\n', response.content)


        return rec
