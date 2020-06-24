import functools
import warnings
from collections.abc import Mapping

from marshmallow import exceptions as ma_exceptions
from webargs.compat import MARSHMALLOW_VERSION_INFO
from webargs.core import _ensure_list_of_callables
from webargs.dict2schema import dict2schema
from webargs.flaskparser import FlaskParser


class ResourceReadingParser(FlaskParser):
    """A version of FlaskParser that can access the resource object it decorates"""

    def use_args(
            self,
            argmap,
            req=None,
            *,
            location=None,
            as_kwargs=False,
            validate=None,
            error_status_code=None,
            error_headers=None,
    ):
        """Decorator that injects parsed arguments into a view function or method.

        Edited from core parser to include the resource object
        """
        location = location or self.location
        request_obj = req
        # Optimization: If argmap is passed as a dictionary, we only need
        # to generate a Schema once
        if isinstance(argmap, Mapping):
            argmap = dict2schema(argmap, schema_class=self.schema_class)()

        def decorator(func):
            req_ = request_obj

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                req_obj = req_

                if not req_obj:
                    req_obj = self.get_request_from_view_args(func, args, kwargs)

                # NOTE: At this point, argmap may be a Schema, or a callable
                parsed_args = self.parse(
                    args[0],  # This should be the self of the resource object
                    argmap,
                    req=req_obj,
                    location=location,
                    validate=validate,
                    error_status_code=error_status_code,
                    error_headers=error_headers,
                )
                args, kwargs = self._update_args_kwargs(
                    args, kwargs, parsed_args, as_kwargs,
                )
                return func(*args, **kwargs)

            wrapper.__wrapped__ = func
            return wrapper

        return decorator

    def parse(
            self,
            resource_object,
            argmap,
            req=None,
            *,
            location=None,
            validate=None,
            error_status_code=None,
            error_headers=None,
    ):
        """Main request parsing method.

        Different from core parser is that we also get the resource object and
        pass it to the schema
        """
        req = req if req is not None else self.get_default_request()
        location = location or self.location
        if req is None:
            raise ValueError("Must pass req object")
        data = None
        validators = _ensure_list_of_callables(validate)
        schema = self._get_schema(argmap, resource_object)
        try:
            location_data = self._load_location_data(
                schema=schema, req=req, location=location,
            )
            result = schema.load(location_data)
            data = result.data if MARSHMALLOW_VERSION_INFO[0] < 3 else result
            self._validate_arguments(data, validators)
        except ma_exceptions.ValidationError as error:
            self._on_validation_error(
                error,
                req,
                schema,
                location,
                error_status_code=error_status_code,
                error_headers=error_headers,
            )
        return data

    def _get_schema(self, argmap, resource_object):
        """Override the behaviour of the standard parser.

        Initialize Schema with a callable that gets the resource object as argument"""
        assert callable(argmap), "Snould only use this parser with a callable"
        schema = argmap(resource_object)

        if MARSHMALLOW_VERSION_INFO[0] < 3 and not schema.strict:
            warnings.warn(
                "It is highly recommended that you set strict=True on your schema "
                "so that the parser's error handler will be invoked when expected.",
                UserWarning,
            )
        return schema


resource_parser = ResourceReadingParser()
