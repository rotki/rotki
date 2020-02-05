from typing import Callable, Dict, Optional, Tuple, Union

from marshmallow import Schema
from werkzeug.local import LocalProxy


class FlaskParser():

    def error_handler(self, func: Callable) -> Callable:
        """Taken from webargs.core.py::Parser"""
        ...

    def use_args(
        self,
        argmap: Union[Schema, Dict, Callable],
        req: Optional[LocalProxy] = None,
        locations: Tuple[str, ...] = None,
        as_kwargs: bool = False,
        validate: Optional[Callable] = None,
        error_status_code: Optional[int] = None,
        error_headers: Dict = None,
    ) -> Callable:
        """Taken from webargs.core.py::Parser

        Example usage with Flask: ::

            @app.route('/echo', methods=['get', 'post'])
            @parser.use_args({'name': fields.Str()})
            def greet(args):
                return 'Hello ' + args['name']

        :param argmap: Either a `marshmallow.Schema`, a `dict`
            of argname -> `marshmallow.fields.Field` pairs, or a callable
            which accepts a request and returns a `marshmallow.Schema`.
        :param tuple locations: Where on the request to search for values.
        :param bool as_kwargs: Whether to insert arguments as keyword arguments.
        :param callable validate: Validation function that receives the dictionary
            of parsed arguments. If the function returns ``False``, the parser
            will raise a :exc:`ValidationError`.
        :param int error_status_code: Status code passed to error handler functions when
            a `ValidationError` is raised.
        :param dict error_headers: Headers passed to error handler functions when a
            a `ValidationError` is raised.
        """
        ...

    def use_kwargs(
        self,
        argmap: Union[Schema, Dict, Callable],
        req: Optional[LocalProxy] = None,
        locations: Tuple[str, ...] = None,
        as_kwargs: bool = False,
        validate: Optional[Callable] = None,
        error_status_code: Optional[int] = None,
        error_headers: Dict = None,
    ) -> Callable:
        """Taken from webargs.core.py::Parser Receives the same args as `use_args`"""
        ...


# Taken from webargs/flaskparser.py
parser = FlaskParser()
use_args = parser.use_args
use_kwargs = parser.use_kwargs
