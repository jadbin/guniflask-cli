import inspect
import os
from collections import defaultdict
from keyword import iskeyword
from os.path import join, exists
from typing import Any, Union

import inflect
import sqlalchemy
from sqlalchemy import ForeignKeyConstraint, CheckConstraint, ForeignKey, Column
from sqlalchemy.util import OrderedDict

from .utils import string_camelcase, string_lowercase_underscore

inflect_engine = inflect.engine()


class SqlToModelGenerator:
    def __init__(self, name, metadata, indent=4, bind=None):
        self.name = name
        self.metadata = metadata
        self.indent = ' ' * indent
        self.bind = bind
        self.collector = None

        many_to_many_tables = set()
        many_to_many_links = defaultdict(list)
        for table in metadata.tables.values():
            fk_constraints = [i for i in table.constraints if isinstance(i, ForeignKeyConstraint)]
            if len(fk_constraints) == 2 and all(col.foreign_keys for col in table.columns):
                many_to_many_tables.add(table.name)
                tablename = sorted(fk_constraints, key=get_constraint_sort_key)[0].elements[0].column.table.name
                many_to_many_links[tablename].append(table)

        self.models = {}
        for table in metadata.sorted_tables:
            if table.name in many_to_many_tables:
                continue
            self.models[table.name] = Model(table, many_to_many_links[table.name])

            # Add many-to-one relations
            for constraint in sorted(table.constraints, key=get_constraint_sort_key):
                if isinstance(constraint, ForeignKeyConstraint):
                    self.models[constraint.elements[0].column.table.name].add_one_to_many_relation(constraint)
                    self.models[constraint.table.name].add_many_to_one_relation(constraint)

    def render(self, path):
        if not exists(path):
            os.makedirs(path)
        model_modules = []
        for model in self.models.values():
            module_name = convert_to_valid_identifier(model.table.name)
            with open(join(path, module_name + '.py'), 'w', encoding='utf-8') as f:
                self.collector = ImportCollector()

                pending = []
                tables_content = self.render_secondary_tables(model)
                if tables_content:
                    pending.append('\n')
                    pending.append(tables_content)
                pending.append('\n\n')
                pending.append(self.render_model(model))

                f.write(self.render_imports())
                for p in pending:
                    f.write(p)

            model_modules.append({'module': module_name, 'class': model.class_name})
        with open(join(path, '__init__.py'), 'w', encoding='utf-8') as f:
            for m in model_modules:
                f.write(f'from .{m["module"]} import {m["class"]}\n')

    def render_imports(self):
        self.collector.add_import('BaseModelMixin', 'guniflask.orm')

        imports = ''
        for k, vlist in self.collector.items():
            for v in vlist:
                if isinstance(v, tuple):
                    imports += f'from {k} import {v[0]} as {v[1]}\n'
                else:
                    imports += f'from {k} import {v}\n'
        if len(self.collector) > 0:
            imports += '\n'
        imports += f'from {self.name}.app import db\n'
        return imports

    def render_model(self, model):
        header_str = f'class {model.class_name}(BaseModelMixin, db.Model):\n'
        header_str += f"{self.indent}__tablename__ = '{model.table.name}'\n"
        if self.bind:
            header_str += f"{self.indent}__bind_key__ = '{self.bind}'\n"
        header_str += '\n'
        columns_str = ''
        for col in model.table.columns:
            attr = convert_to_valid_identifier(col.name)
            show_name = attr != col.name
            columns_str += f'{self.indent}{attr} = {self.render_column(col, show_name=show_name)}\n'
        relationships_str = ''
        for r in model.relationships:
            relationships_str += self.indent + self.render_relationship(r) + '\n'
        return header_str + columns_str + relationships_str

    def render_secondary_tables(self, model):
        return '\n'.join([self.render_table(r.association_table) for r in model.relationships
                          if isinstance(r, ManyToManyRelationship)])

    def render_table(self, table):
        columns_str = ',\n'.join(self.indent + self.render_column(col, show_name=True) for col in table.columns)
        tablename = convert_to_valid_identifier(table.name)
        return f'{tablename} = db.Table({table.name!r},\n{columns_str}\n)\n'

    def render_column(self, column, show_name=False):
        if column.server_default:
            self.collector.add_import(('text', '_text'), 'sqlalchemy')
        self.collector.add_import(column.type)

        is_sole_pk = column.primary_key and len(column.table.primary_key) == 1
        dedicated_fks = [c for c in column.foreign_keys if len(c.constraint.columns) == 1]
        is_unique = ColumnUtils.is_unique(column)
        has_index = ColumnUtils.has_index(column)
        server_default = None

        render_coltype = not dedicated_fks or any(fk.column is column for fk in dedicated_fks)

        kwargs = []
        if column.key != column.name:
            kwargs.append('key')
        if column.primary_key:
            kwargs.append('primary_key')
        if column.autoincrement is True:
            kwargs.append('autoincrement')
        if not column.nullable and not is_sole_pk:
            kwargs.append('nullable')
        if is_unique:
            column.unique = True
            kwargs.append('unique')
        if has_index:
            column.index = True
            kwargs.append('index')
        if column.comment:
            kwargs.append('comment')
        if column.server_default:
            default_expr = self.get_compiled_expression(column.server_default.arg)
            if '\n' in default_expr:
                server_default = f'server_default=_text("""\\\n{default_expr}""")'
            else:
                default_expr = default_expr.replace('"', '\\"')
                server_default = f'server_default=_text("{default_expr}")'
        return "db.Column({})".format(
            ', '.join(
                ([repr(column.name)] if show_name else []) +
                ([self.render_column_type(column.type)] if render_coltype else []) +
                [self.render_constraint(x) for x in dedicated_fks] +
                [f'{i}={getattr(column, i)!r}' for i in kwargs] +
                ([server_default] if server_default else [])
            )
        )

    def render_column_type(self, coltype):
        argspec = inspect.getfullargspec(coltype.__class__.__init__)
        defaults = dict(
            zip(
                argspec.args[-len(argspec.defaults or ()):],
                argspec.defaults or (),
            )
        )

        args = []
        kwargs = OrderedDict()
        use_kwargs = False
        missing = object()

        for attr in argspec.args[1:]:
            if attr.startswith('_'):
                continue

            value = getattr(coltype, attr, missing)
            default = defaults.get(attr, missing)
            if value is missing or value == default:
                use_kwargs = True
            else:
                if use_kwargs:
                    kwargs[attr] = repr(value)
                else:
                    args.append(repr(value))
                self.collector.add_import(type(value))

        if isinstance(coltype, sqlalchemy.Enum) and coltype.name is not None:
            kwargs['name'] = repr(coltype.name)

        for key, value in kwargs.items():
            args.append('{}={}'.format(key, value))

        rendered = coltype.__class__.__name__
        if args:
            rendered += f'({", ".join(args)})'
        return rendered

    def render_constraint(self, constraint):
        def render_fk_options(*args):
            opts = [repr(i) for i in args]
            for attr in 'ondelete', 'onupdate':
                value = getattr(constraint, attr, None)
                if value:
                    opts.append(f'{attr}={value!r}')
            return ', '.join(opts)

        if isinstance(constraint, ForeignKey):
            remote_column = f'{constraint.column.table.name}.{constraint.column.name}'
            return f'db.ForeignKey({render_fk_options(remote_column)})'

    def render_relationship(self, relationship):
        kwargs_str = ', '.join(
            [repr(table_name_to_class_name(relationship.target_tbl))] +
            [f'{i}={relationship.kwargs[i]}' for i in sorted(relationship.kwargs.keys())]
        )
        return f'{relationship.preferred_name} = db.relationship({kwargs_str})'

    def get_compiled_expression(self, statement):
        return str(statement.compile(
            self.metadata.bind, compile_kwargs={"literal_binds": True}))


def convert_to_valid_identifier(name):
    name = string_lowercase_underscore(name)
    if name[0].isdigit() or iskeyword(name):
        name = '_' + name
    return name


def table_name_to_class_name(table_name):
    name = string_camelcase(table_name)
    if name[0].isdigit():
        name = '_' + name
    return name


def get_constraint_sort_key(constraint):
    if isinstance(constraint, CheckConstraint):
        return f'C{constraint.sqltext}'
    return constraint.__class__.__name__[0] + repr(list(constraint.columns.keys()))


def is_one_to_one_relationship(constraint):
    if isinstance(constraint, ForeignKeyConstraint):
        if len(constraint.columns) == 1 and any(ColumnUtils.is_unique(col) for col in constraint.columns):
            return True
    return False


class ColumnUtils:
    @staticmethod
    def is_unique(column: Column):
        return any(i.unique and set(i.columns) == {column} for i in column.table.indexes)

    @staticmethod
    def has_index(column: Column):
        return any(set(i.columns) == {column} for i in column.table.indexes)


class Model:
    parent_name = 'db.Model'

    def __init__(self, table, association_tables):
        self.table = table
        self.class_name = table_name_to_class_name(table.name)
        self.relationships = []

        # Add many-to-many relationships
        for association_table in association_tables:
            fk_constraints = [c for c in association_table.constraints if isinstance(c, ForeignKeyConstraint)]
            fk_constraints.sort(key=get_constraint_sort_key)
            target_tbl = fk_constraints[1].elements[0].column.table.name
            relationship = ManyToManyRelationship(self.table.name, target_tbl, association_table)
            self.relationships.append(relationship)

    def add_one_to_many_relation(self, constraint):
        relationship = OneToManyRelationship(self.table.name, constraint.table.name, constraint)
        self.relationships.append(relationship)

    def add_many_to_one_relation(self, constraint):
        relationship = ManyToOneRelationship(self.table.name, constraint.elements[0].column.table.name, constraint)
        self.relationships.append(relationship)


class Relationship:
    def __init__(self, source_tbl, target_tbl):
        self.source_tbl = source_tbl
        self.target_tbl = target_tbl
        self.kwargs = {}
        self.preferred_name = None


class ManyToOneRelationship(Relationship):
    def __init__(self, source_tbl, target_tbl, constraint):
        super().__init__(source_tbl, target_tbl)

        self.preferred_name = convert_to_valid_identifier(target_tbl)
        self.constraint = constraint
        self.kwargs['lazy'] = repr('joined')

        back_populates = convert_to_valid_identifier(source_tbl)
        if not is_one_to_one_relationship(constraint):
            back_populates = inflect_engine.plural(back_populates)
        self.kwargs['back_populates'] = repr(f'{back_populates}')


class OneToManyRelationship(Relationship):
    def __init__(self, source_tbl, target_tbl, constraint):
        super().__init__(source_tbl, target_tbl)

        self.preferred_name = convert_to_valid_identifier(target_tbl)
        self.constraint = constraint

        # Add uselist=False to one-to-one relationships
        if is_one_to_one_relationship(constraint):
            self.kwargs['uselist'] = False
            self.kwargs['lazy'] = repr('joined')
        else:
            self.preferred_name = inflect_engine.plural(self.preferred_name)
            self.kwargs['lazy'] = repr('select')
        self.kwargs['back_populates'] = repr(f'{convert_to_valid_identifier(source_tbl)}')


class ManyToManyRelationship(Relationship):
    def __init__(self, source_tbl, target_tbl, association_table):
        super().__init__(source_tbl, target_tbl)

        self.preferred_name = inflect_engine.plural(convert_to_valid_identifier(target_tbl))
        self.association_table = association_table

        self.kwargs['secondary'] = convert_to_valid_identifier(association_table.name)
        self.kwargs['lazy'] = repr('select')
        self.kwargs['backref'] = "db.backref({}, lazy='select')".format(
            repr(inflect_engine.plural(convert_to_valid_identifier(source_tbl)))
        )


class ImportCollector(OrderedDict):
    def add_import(self, name: Any, pkg: Union[str, tuple] = None):
        if not isinstance(name, (str, tuple)):
            if inspect.isclass(name):
                obj_type = name
            else:
                obj_type = type(name)
            pkg = obj_type.__module__
            name = obj_type.__name__

            if pkg == 'builtins':
                return

        names = self.setdefault(pkg, set())
        names.add(name)
