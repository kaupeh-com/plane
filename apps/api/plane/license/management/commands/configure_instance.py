# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import os

# Django imports
from django.core.management.base import BaseCommand, CommandError

# Module imports
from plane.license.models import InstanceConfiguration
from plane.utils.instance_config_variables import instance_config_variables


class Command(BaseCommand):
    help = "Configure instance variables"

    def handle(self, *args, **options):
        from plane.license.utils.encryption import encrypt_data
        from plane.license.utils.instance_value import get_configuration_value

        mandatory_keys = ["SECRET_KEY"]

        for item in mandatory_keys:
            if not os.environ.get(item):
                raise CommandError(f"{item} env variable is required.")

        for item in instance_config_variables:
            value = encrypt_data(item.get("value")) if item.get("is_encrypted", False) else item.get("value")
            obj, created = InstanceConfiguration.objects.update_or_create(
                key=item.get("key"),
                defaults={
                    "category": item.get("category"),
                    "is_encrypted": item.get("is_encrypted", False),
                    "value": value,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"{obj.key} loaded with value from environment variable."))
            else:
                self.stdout.write(self.style.SUCCESS(f"{obj.key} updated with value from environment variable."))
