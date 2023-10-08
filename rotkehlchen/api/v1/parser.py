import functools
from collections.abc import Mapping
from typing import Any, Callable, Optional

from flask.views import MethodView
from marshmallow import Schema, exceptions as ma_exceptions
from webargs.core import (
    _UNKNOWN_DEFAULT_PARAM,
    ArgMap,
    Request,
    ValidateArg,
    _ensure_list_of_callables,
)
from webargs.flaskparser import FlaskParser


class ResourceReadingParser(FlaskParser):
    """A version of FlaskParser that can access the resource object it decorates"""

    def use_args(
            self,
            argmap: ArgMap,
            req: Optional[Request] = None,
            *,
            location: Optional[str] = None,
            unknown: Optional[str] = _UNKNOWN_DEFAULT_PARAM,  # pylint: disable=unused-argument
            as_kwargs: bool = False,
            validate: Optional[ValidateArg] = None,
            error_status_code: Optional[int] = None,
            error_headers: Optional[Mapping[str, str]] = None,
    ) -> Callable:
        """Decorator that injects parsed arguments into a view function or method.

        Edited from core parser to include the resource object
        """
        location = location or self.location
        request_obj = req
        # Optimization: If argmap is passed as a dictionary, we only need
        # to generate a Schema once
        if isinstance(argmap, Mapping):
            argmap = Schema.from_dict(argmap)()

        def decorator(func: Callable) -> Callable:
            req_ = request_obj

            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Callable:
                req_obj = req_

                if not req_obj:
                    req_obj = self.get_request_from_view_args(func, args, kwargs)  # pylint: disable=assignment-from-none

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
                args, kwargs = self._update_args_kwargs(  # type: ignore
                    args, kwargs, parsed_args, as_kwargs,  # type: ignore
                )
                return func(*args, **kwargs)

            wrapper.__wrapped__ = func  # type: ignore
            return wrapper

        return decorator

    def parse(  # type: ignore  # we have added the resource_object on top of parse
            self,
            resource_object: MethodView,
            argmap: ArgMap,
            req: Optional[Request] = None,
            *,
            location: Optional[str] = None,
            unknown: Optional[str] = _UNKNOWN_DEFAULT_PARAM,  # pylint: disable=unused-argument
            validate: Optional[ValidateArg] = None,
            error_status_code: Optional[int] = None,
            error_headers: Optional[Mapping[str, str]] = None,
    ) -> dict[str, Any]:
        """Main request parsing method.

        Different from core parser is that we also get the resource object and
        pass it to the schema
        """
        req = req if req is not None else self.get_default_request()  # type: ignore
        location = location or self.location
        if req is None:
            raise ValueError('Must pass req object')
        data = None
        validators = _ensure_list_of_callables(validate)
        schema = self._get_schema(argmap, resource_object)
        try:
            location_data = self._load_location_data(
                schema=schema, req=req, location=location,
            )
            data = schema.load(location_data)
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

    def _get_schema(
            self,
            argmap: ArgMap,
            resource_object: Request,
    ) -> Schema:
        """Override the behaviour of the standard parser.

        Initialize Schema with a callable that gets the resource object as argument"""
        assert callable(argmap), 'Should only use this parser with a callable'
        schema = argmap(resource_object)

        return schema


class IgnoreKwargAfterPostLoadParser(FlaskParser):
    """A version of FlaskParser that does not augment with kwarg arguments after post_load"""

    @staticmethod
    def _update_args_kwargs(  # type: ignore
        args: tuple,
        kwargs: dict[str, Any],
        parsed_args: Mapping,
        as_kwargs: bool,
    ) -> tuple[tuple, Mapping]:
        return args, parsed_args


resource_parser = ResourceReadingParser()
ignore_kwarg_parser = IgnoreKwargAfterPostLoadParser()
