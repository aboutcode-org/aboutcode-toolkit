from schematics.models import Model
from schematics.types import StringType
from schematics.exceptions import ValidationError
from schematics.types import BaseType

class About(Model):
    # The min_length is needed to make sure the key has value
    # Otherwise, an empty value key is accepted.
    name = StringType(required=True, min_length = 1)
    version = StringType(required=True, min_length = 1)

    MESSAGES = {
        'empty': ' : Field is empty.'
    }

    def validate_empty_value(self, about):
        for k in about.keys():
            if len(about[k]) < 1:
                raise ValidationError(k + self.MESSAGES['empty'])