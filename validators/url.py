""" Моудль валидатора URL """

import re
from urllib.parse import urlsplit, urlunsplit
from django.core.validators import URLValidator, validate_ipv6_address, RegexValidator, _lazy_re_compile
from django.core.exceptions import ValidationError


class VariableSchemeUrlValidator(URLValidator):
    """ Валидатор URL который не проверяет схему URL """

    regex = _lazy_re_compile(
        r'(?:\S+(?::\S*)?@)?'  # user:pass authentication
        r'(?:' + URLValidator.ipv4_re + '|' + URLValidator.ipv6_re + '|' + URLValidator.host_re + ')'
        r'(?::\d{2,5})?'  # port
        r'(?:[/?#][^\s]*)?'  # resource path
        r'\Z', re.IGNORECASE)

    def __call__(self, value):
        if '://' in value:
            scheme = value.split('://')[0].lower()
        else:
            scheme = None

        # отключаю проверку схемы url
        if scheme:
            if scheme not in self.schemes:
                raise ValidationError(self.message, code=self.code)

        try:
            super(URLValidator, self).__call__(value)
        except ValidationError as e:
            if value:
                try:
                    scheme, netloc, path, query, fragment = urlsplit(value)
                except ValueError:  # for example, "Invalid IPv6 URL"
                    raise ValidationError(self.message, code=self.code)
                try:
                    netloc = netloc.encode('idna').decode('ascii')  # IDN -> ACE
                except UnicodeError:  # invalid domain part
                    raise e
                url = urlunsplit((scheme, netloc, path, query, fragment))
                super().__call__(url)
            else:
                raise
        else:
            # Now verify IPv6 in the netloc part
            host_match = re.search(r'^\[(.+)\](?::\d{2,5})?$', urlsplit(value).netloc)
            if host_match:
                potential_ip = host_match.groups()[0]
                try:
                    validate_ipv6_address(potential_ip)
                except ValidationError:
                    raise ValidationError(self.message, code=self.code)

        # The maximum length of a full host name is 253 characters per RFC 1034
        # section 3.1. It's defined to be 255 bytes or less, but this includes
        # one byte for the length of the name and one byte for the trailing dot
        # that's used to indicate absolute names in DNS.
        if len(urlsplit(value).netloc) > 253:
            raise ValidationError(self.message, code=self.code)