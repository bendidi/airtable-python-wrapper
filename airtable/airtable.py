"""

Airtable Class Instance
***********************

>>> airtable = Airtable('base_key', 'table_name')
>>> airtable.get_all()
[{id:'rec123asa23', fields': {'Column': 'Value'}, ...}]

For more information on Api Key and authentication see
the :doc:`authentication`.

------------------------------------------------------------------------

Examples
********

For a full list of available methods see the :any:`Airtable` class below.
For more details on the Parameter filters see the documentation on the
available :doc:`params` as well as the
`Airtable API Docs <http://airtable.com/api>`_

Record/Page Iterator:

>>> for page in airtable.get_iter(view='ViewName',sort='COLUMN_A'):
...     for record in page:
...         value = record['fields']['COLUMN_A']

Get all Records:

>>> airtable.get_all(view='ViewName',sort='COLUMN_A')
[{id:'rec123asa23', 'fields': {'COLUMN_A': 'Value', ...}, ... ]

Search:

>>> airtable.search('ColumnA', 'SearchValue')

Formulas:

>>> airtable.get_all(formula="FIND('DUP', {COLUMN_STR})=1")


Insert:

>>> airtable.insert({'First Name', 'John'})

Delete:

>>> airtable.delete('recwPQIfs4wKPyc9D')


You can see the Airtable Class in action in this
`Jupyter Notebook <https://github.com/gtalarico/airtable-python-wrapper/blob/master/Airtable.ipynb>`_

------------------------------------------------------------------------

Return Values
**************

Return Values: when records are returned,
they will most often be a list of Airtable records (dictionary) in a format
similar to this:

>>> [{
...     "records": [
...         {
...             "id": "recwPQIfs4wKPyc9D",
...             "fields": {
...                 "COLUMN_ID": "1",
...             },
...             "createdTime": "2017-03-14T22:04:31.000Z"
...         },
...         {
...             "id": "rechOLltN9SpPHq5o",
...             "fields": {
...                 "COLUMN_ID": "2",
...             },
...             "createdTime": "2017-03-20T15:21:50.000Z"
...         },
...         {
...             "id": "rec5eR7IzKSAOBHCz",
...             "fields": {
...                 "COLUMN_ID": "3",
...             },
...             "createdTime": "2017-08-05T21:47:52.000Z"
...         }
...     ],
...     "offset": "rec5eR7IzKSAOBHCz"
... }, ... ]

"""  #

import sys
import requests
from functools import partial
from collections import OrderedDict
import posixpath
import time
import json
from six.moves.urllib.parse import unquote, quote

from .auth import AirtableAuth
from .params import AirtableParams

try:
    IS_IPY = sys.implementation.name == "ironpython"
except AttributeError:
    IS_IPY = False


class AirtableBase:

    VERSION = "v0"
    API_BASE_URL = "https://api.airtable.com/"
    API_LIMIT = 1.0 / 5  # 5 per second
    API_URL = posixpath.join(API_BASE_URL, VERSION)

    def __init__(self, base_key, api_key=None):
        """
        If api_key is not provided, :any:`AirtableAuth` will attempt
        to use ``os.environ['AIRTABLE_API_KEY']``
        """
        session = requests.Session()
        session.auth = AirtableAuth(api_key=api_key)
        self.session = session

        self.base_url = posixpath.join(self.API_URL, base_key)

    def _process_params(self, params):
        """
        Process params names or values as needed using filters
        """
        new_params = OrderedDict()
        for param_name, param_value in sorted(params.items()):
            param_value = params[param_name]
            params_class = AirtableParams._get(param_name)
            new_params.update(params_class(
                param_value).to_param_dict())
        return new_params

    def _process_response(self, response):
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            err_msg = str(exc)

            # Reports Decoded 422 Url for better troubleshooting
            # Disabled in IronPython Bug:
            # https://github.com/IronLanguages/ironpython2/issues/242
            if not IS_IPY and response.status_code == 422:
                err_msg = err_msg.replace(response.url, unquote(response.url))
                err_msg += " (Decoded URL)"

            # Attempt to get Error message from response, Issue #16
            try:
                error_dict = response.json()
            except json.decoder.JSONDecodeError:
                pass
            else:
                if "error" in error_dict:
                    err_msg += " [Error: {}]".format(error_dict["error"])
            raise requests.exceptions.HTTPError(err_msg)
        else:
            return response.json()

    def record_table_url(self, table_name, record_id):
        """ Builds URL with record id """
        url_safe_table_name = quote(table_name, safe="")
        return posixpath.join(self.base_url, url_safe_table_name, record_id)

    def _request(self, method, url, params=None, json_data=None):
        response = self.session.request(method, url, params=params, json=json_data)
        return self._process_response(response)

    def _get(self, url, **params):
        processed_params = self._process_params(params)
        return self._request("get", url, params=processed_params)

    def _post(self, url, json_data):
        return self._request("post", url, json_data=json_data)

    def _put(self, url, json_data):
        return self._request("put", url, json_data=json_data)

    def _patch(self, url, json_data):
        return self._request("patch", url, json_data=json_data)

    def _delete(self, url):
        return self._request("delete", url)

    def get_in_table(self, table_name, record_id):
        """
        Retrieves a record by its id
        >>> record = airtable.get_in_table('table_name', 'recwPQIfs4wKPyc9D')
        Args:
            table_name(``str``): Airtable table name
            record_id(``str``): Airtable record id
        Returns:
            record (``dict``): Record
        """
        url = self.record_table_url(table_name, record_id)
        return self._get(url)

    def get_iter_in_table(self, table_name, **options):
        """
        Record Retriever Iterator
        Returns iterator with lists in batches according to pageSize.
        To get all records at once use :any:`get_all`
        >>> for page in airtable.get_iter_in_table(table_name):
        ...     for record in page:
        ...         print(record)
        [{'fields': ... }, ...]
        Args:
            table_name(``str``): Airtable table name
        Keyword Args:
            max_records (``int``, optional): The maximum total number of
                records that will be returned. See :any:`MaxRecordsParameter`
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParameter`.
            page_size (``int``, optional ): The number of records returned
                in each request. Must be less than or equal to 100.
                Default is 100. See :any:`PageSizeParameter`.
            fields (``str``, ``list``, optional): Name of field or fields to
                be retrieved. Default is all fields. See :any:`FieldsParameter`.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending. See :any:`SortParameter`.
            formula (``str``, optional): Airtable formula.
                See :any:`FormulaParameter`.
        Returns:
            iterator (``list``): List of Records, grouped by pageSize
        """
        offset = None
        url_safe_table_name = quote(table_name, safe="")
        url = posixpath.join(self.base_url, url_safe_table_name)
        while True:
            data = self._get(url, offset=offset, **options)
            records = data.get("records", [])
            time.sleep(self.API_LIMIT)
            yield records
            offset = data.get("offset")
            if not offset:
                break

    def get_all_in_table(self, table_name, **options):
        """
        Retrieves all records repetitively and returns a single list.
        >>> airtable.get_all_in_table('table_name')
        >>> airtable.get_all_in_table('table_name', view='MyView', fields=['ColA', '-ColB'])
        >>> airtable.get_all_in_table('table_name', maxRecords=50)
        [{'fields': ... }, ...]
        Args:
            table_name(``str``): Airtable table name
        Keyword Args:
            max_records (``int``, optional): The maximum total number of
                records that will be returned. See :any:`MaxRecordsParameter`
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParameter`.
            fields (``str``, ``list``, optional): Name of field or fields to
                be retrieved. Default is all fields. See :any:`FieldsParameter`.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending. See :any:`SortParameter`.
            formula (``str``, optional): Airtable formula.
                See :any:`FormulaParameter`.
        Returns:
            records (``list``): List of Records
        >>> records = get_all(maxRecords=3, view='All')
        """
        all_records = []
        for records in self.get_iter_in_table(table_name, **options):
            all_records.extend(records)
        return all_records

    def match_in_table(self, table_name, field_name, field_value, **options):
        """
        Returns first match found in :any:`get_all`
        >>> airtable.match_in_table('table_name', 'Name', 'John')
        {'fields': {'Name': 'John'} }
        Args:
            table_name(``str``): Airtable table name
            field_name (``str``): Name of field to match (column name).
            field_value (``str``): Value of field to match.
        Keyword Args:
            max_records (``int``, optional): The maximum total number of
                records that will be returned. See :any:`MaxRecordsParameter`
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParameter`.
            fields (``str``, ``list``, optional): Name of field or fields to
                be retrieved. Default is all fields. See :any:`FieldsParameter`.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending. See :any:`SortParameter`.
        Returns:
            record (``dict``): First record to match the field_value provided
        """
        from_name_and_value = AirtableParams.FormulaParameter.from_name_and_value
        formula = from_name_and_value(field_name, field_value)
        options["formula"] = formula
        for record in self.get_all_in_table(table_name, **options):
            return record
        return {}

    def search_in_table(self, table_name, field_name, field_value, **options):
        """
        Returns all matching records found in :any:`get_all`
        >>> airtable.search_in_table('table_name', 'Gender', 'Male')
        [{'fields': {'Name': 'John', 'Gender': 'Male'}, ... ]
        Args:
            table_name(``str``): Airtable table name
            field_name (``str``): Name of field to match (column name).
            field_value (``str``): Value of field to match.
        Keyword Args:
            max_records (``int``, optional): The maximum total number of
                records that will be returned. See :any:`MaxRecordsParameter`
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParameter`.
            fields (``str``, ``list``, optional): Name of field or fields to
                be retrieved. Default is all fields. See :any:`FieldsParameter`.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending. See :any:`SortParameter`.
        Returns:
            records (``list``): All records that matched ``field_value``
        """
        records = []
        from_name_and_value = AirtableParams.FormulaParameter.from_name_and_value
        formula = from_name_and_value(field_name, field_value)
        options["formula"] = formula
        records = self.get_all_in_table(table_name, **options)
        return records

    def insert_in_table(self, table_name, fields, typecast=False):
        """
        Inserts a record
        >>> record = {'Name': 'John'}
        >>> airtable.insert_in_table('table_name', record)
        Args:
            table_name(``str``): Airtable table name
            fields(``dict``): Fields to insert.
                Must be dictionary with Column names as Key.
            typecast(``boolean``): Automatic data conversion from string values.
        Returns:
            record (``dict``): Inserted record
        """
        url_safe_table_name = quote(table_name, safe="")
        url = posixpath.join(self.base_url, url_safe_table_name)
        return self._post(
            url, json_data={"fields": fields, "typecast": typecast}
        )

    def _batch_request(self, func, iterable):
        """ Internal Function to limit batch calls to API limit """
        responses = []
        for item in iterable:
            responses.append(func(item))
            time.sleep(self.API_LIMIT)
        return responses

    def batch_insert_in_table(self, table_name, records, typecast=False):
        """
        Calls :any:`insert` repetitively, following set API Rate Limit (5/sec)
        To change the rate limit use ``airtable.API_LIMIT = 0.2``
        (5 per second)
        >>> records = [{'Name': 'John'}, {'Name': 'Marc'}]
        >>> airtable.batch_insert_in_table('table_name', records)
        Args:
            table_name(``str``): Airtable table name
            records(``list``): Records to insert
        Returns:
            records (``list``): list of added records
        """
        table_insert = partial(self.insert_in_table, table_name, typecast=typecast)
        return self._batch_request(table_insert, records)

    def update_in_table(self, table_name, record_id, fields, typecast=False):
        """
        Updates a record by its record id.
        Only Fields passed are updated, the rest are left as is.
        >>> record = airtable.match_in_table('table_name', 'Employee Id', 'DD13332454')
        >>> fields = {'Status': 'Fired'}
        >>> airtable.update_in_table('table_name', record['id'], fields)
        Args:
            table_name(``str``): Airtable table name
            fields(``dict``): Fields to update.
                Must be dictionary with Column names as Key
            typecast(``boolean``): Automatic data conversion from string values.
        Returns:
            record (``dict``): Updated record
        """
        url = self.record_table_url(table_name, record_id)
        return self._patch(
            url, json_data={"fields": fields, "typecast": typecast}
        )

    def update_by_field_in_table(
        self, table_name, field_name, field_value, fields, typecast=False, **options
    ):
        """
        Updates the first record to match field name and value.
        Only Fields passed are updated, the rest are left as is.
        >>> record = {'Name': 'John', 'Tel': '540-255-5522'}
        >>> airtable.update_by_field_in_table('table_name', 'Name', 'John', record)
        Args:
            table_name(``str``): Airtable table name
            field_name (``str``): Name of field to match (column name).
            field_value (``str``): Value of field to match.
            fields(``dict``): Fields to update.
                Must be dictionary with Column names as Key
            typecast(``boolean``): Automatic data conversion from string values.
        Keyword Args:
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParameter`.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending. See :any:`SortParameter`.
        Returns:
            record (``dict``): Updated record
        """
        record = self.match_in_table(table_name, field_name, field_value, **options)
        return {} if not record else self.update(table_name, record["id"], fields, typecast)

    def replace_in_table(self, table_name, record_id, fields, typecast=False):
        """
        Replaces a record by its record id.
        All Fields are updated to match the new ``fields`` provided.
        If a field is not included in ``fields``, value will bet set to null.
        To update only selected fields, use :any:`update`.
        >>> record = airtable.match('Seat Number', '22A')
        >>> fields = {'PassangerName': 'Mike', 'Passport': 'YASD232-23'}
        >>> airtable.replace_in_table('table_name', record['id'], fields)
        Args:
            table_name(``str``): Airtable table name
            record_id(``str``): Id of Record to update
            fields(``dict``): Fields to replace with.
                Must be dictionary with Column names as Key.
            typecast(``boolean``): Automatic data conversion from string values.
        Returns:
            record (``dict``): New record
        """
        record_url = self.record_table_url(table_name, record_id)
        return self._put(record_url, json_data={"fields": fields, "typecast": typecast})

    def replace_by_field_in_table(
        self, table_name, field_name, field_value, fields, typecast=False, **options
    ):
        """
        Replaces the first record to match field name and value.
        All Fields are updated to match the new ``fields`` provided.
        If a field is not included in ``fields``, value will bet set to null.
        To update only selected fields, use :any:`update`.
        Args:
            table_name(``str``): Airtable table name
            field_name (``str``): Name of field to match (column name).
            field_value (``str``): Value of field to match.
            fields(``dict``): Fields to replace with.
                Must be dictionary with Column names as Key.
            typecast(``boolean``): Automatic data conversion from string values.
        Keyword Args:
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParameter`.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending. See :any:`SortParameter`.
        Returns:
            record (``dict``): New record
        """
        record = self.match_in_table(table_name, field_name, field_value, **options)
        return {} if not record else self.replace_in_table(table_name, record["id"], fields, typecast)

    def delete_in_table(self, table_name, record_id):
        """
        Deletes a record by its id
        >>> record = airtable.match('table_name', 'Employee Id', 'DD13332454')
        >>> airtable.delete(record['id'])
        Args:
            table_name(``str``): Airtable table name
            record_id(``str``): Airtable record id
        Returns:
            record (``dict``): Deleted Record
        """
        record_url = self.record_table_url(table_name, record_id)
        return self._delete(record_url)

    def delete_by_field_in_table(self, table_name, field_name, field_value, **options):
        """
        Deletes first record  to match provided ``field_name`` and
        ``field_value``.
        >>> record = airtable.delete_by_field('table_name', 'Employee Id', 'DD13332454')
        Args:
            table_name(``str``): Airtable table name
            field_name (``str``): Name of field to match (column name).
            field_value (``str``): Value of field to match.
        Keyword Args:
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParameter`.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending. See :any:`SortParameter`.
        Returns:
            record (``dict``): Deleted Record
        """
        record = self.match_in_table(table_name, field_name, field_value, **options)
        record_url = self.record_table_url(table_name, record["id"])
        return self._delete(record_url)

    def batch_delete(self, table_name, record_ids):
        """
        Calls :any:`delete` repetitively, following set API Rate Limit (5/sec)
        To change the rate limit set value of ``airtable.API_LIMIT`` to
        the time in seconds it should sleep before calling the function again.
        >>> record_ids = ['recwPQIfs4wKPyc9D', 'recwDxIfs3wDPyc3F']
        >>> airtable.batch_delete('table_name', records_ids)
        Args:
            table_name(``str``): Airtable table name
            records(``list``): Record Ids to delete
        Returns:
            records(``list``): list of records deleted
        """
        table_delete = partial(self.delete_in_table, table_name)
        return self._batch_request(table_delete, record_ids)

    def mirror_in_table(self, table_name, records, **options):
        """
        Deletes all records on table or view and replaces with records.
        >>> records = [{'Name': 'John'}, {'Name': 'Marc'}]
        >>> record = airtable.mirror_in_table('table_name', records)
        If view options are provided, only records visible on that view will
        be deleted.
        >>> record = airtable.mirror_in_table('table_name', records, view='View')
        ([{'id': 'recwPQIfs4wKPyc9D', ... }], [{'deleted': True, ... }])
        Args:
            table_name(``str``): Airtable table name
            records(``list``): Records to insert
        Keyword Args:
            max_records (``int``, optional): The maximum total number of
                records that will be returned. See :any:`MaxRecordsParameter`
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParameter`.
        Returns:
            records (``tuple``): (new_records, deleted_records)
        """

        all_record_ids = [r["id"] for r in self.get_all(table_name, **options)]
        deleted_records = self.batch_delete_in_table(table_name, all_record_ids)
        new_records = self.batch_insert_in_table(table_name, records)
        return (new_records, deleted_records)


class Airtable(AirtableBase):

    def __init__(self, base_key, table_name, api_key=None):
        """
        If api_key is not provided, :any:`AirtableAuth` will attempt
        to use ``os.environ['AIRTABLE_API_KEY']``
        """
        super().__init__(base_key, api_key=api_key)
        self.table_name = table_name

        # the 2 lines below are not really needed but kept just for passing tests
        # and more importantly for backward comptability
        # @TODO: breaking change to remove in next release
        url_safe_table_name = quote(table_name, safe="")
        self.url_table = posixpath.join(self.API_URL, base_key, url_safe_table_name)

    # same for this function, not really needed too
    # @TODO: breaking change to add in next release

    def record_url(self, record_id):
        """ Builds URL with record id """
        return posixpath.join(self.url_table, record_id)

    def get(self, record_id):
        """
        Retrieves a record by its id

        >>> record = airtable.get('recwPQIfs4wKPyc9D')

        Args:
            record_id(``str``): Airtable record id

        Returns:
            record (``dict``): Record
        """
        return self.get_in_table(self.table_name, record_id)

    def get_iter(self, **options):
        """
        Record Retriever Iterator

        Returns iterator with lists in batches according to pageSize.
        To get all records at once use :any:`get_all`

        >>> for page in airtable.get_iter():
        ...     for record in page:
        ...         print(record)
        [{'fields': ... }, ...]

        Keyword Args:
            max_records (``int``, optional): The maximum total number of
                records that will be returned. See :any:`MaxRecordsParam`
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParam`.
            page_size (``int``, optional ): The number of records returned
                in each request. Must be less than or equal to 100.
                Default is 100. See :any:`PageSizeParam`.
            fields (``str``, ``list``, optional): Name of field or fields to
                be retrieved. Default is all fields. See :any:`FieldsParam`.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending. See :any:`SortParam`.
            formula (``str``, optional): Airtable formula.
                See :any:`FormulaParam`.

        Returns:
            iterator (``list``): List of Records, grouped by pageSize

        """
        return self.get_iter_in_table(self.table_name, **options)

    def get_all(self, **options):
        """
        Retrieves all records repetitively and returns a single list.

        >>> airtable.get_all()
        >>> airtable.get_all(view='MyView', fields=['ColA', '-ColB'])
        >>> airtable.get_all(maxRecords=50)
        [{'fields': ... }, ...]

        Keyword Args:
            max_records (``int``, optional): The maximum total number of
                records that will be returned. See :any:`MaxRecordsParam`
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParam`.
            fields (``str``, ``list``, optional): Name of field or fields to
                be retrieved. Default is all fields. See :any:`FieldsParam`.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending. See :any:`SortParam`.
            formula (``str``, optional): Airtable formula.
                See :any:`FormulaParam`.

        Returns:
            records (``list``): List of Records

        >>> records = get_all(maxRecords=3, view='All')

        """
        return self.get_all_in_table(self.table_name, **options)

    def match(self, field_name, field_value, **options):
        """
        Returns first match found in :any:`get_all`

        >>> airtable.match('Name', 'John')
        {'fields': {'Name': 'John'} }

        Args:
            field_name (``str``): Name of field to match (column name).
            field_value (``str``): Value of field to match.

        Keyword Args:
            max_records (``int``, optional): The maximum total number of
                records that will be returned. See :any:`MaxRecordsParam`
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParam`.
            fields (``str``, ``list``, optional): Name of field or fields to
                be retrieved. Default is all fields. See :any:`FieldsParam`.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending. See :any:`SortParam`.

        Returns:
            record (``dict``): First record to match the field_value provided
        """
        return self.match_in_table(self.table_name, field_name, field_value, **options)

    def search(self, field_name, field_value, **options):
        """
        Returns all matching records found in :any:`get_all`

        >>> airtable.search('Gender', 'Male')
        [{'fields': {'Name': 'John', 'Gender': 'Male'}, ... ]

        Args:
            field_name (``str``): Name of field to match (column name).
            field_value (``str``): Value of field to match.

        Keyword Args:
            max_records (``int``, optional): The maximum total number of
                records that will be returned. See :any:`MaxRecordsParam`
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParam`.
            fields (``str``, ``list``, optional): Name of field or fields to
                be retrieved. Default is all fields. See :any:`FieldsParam`.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending. See :any:`SortParam`.

        Returns:
            records (``list``): All records that matched ``field_value``

        """

        return self.search_in_table(self.table_name, field_name, field_value, **options)

    def insert(self, fields, typecast=False):
        """
        Inserts a record

        >>> record = {'Name': 'John'}
        >>> airtable.insert(record)

        Args:
            fields(``dict``): Fields to insert.
                Must be dictionary with Column names as Key.
            typecast(``boolean``): Automatic data conversion from string values.

        Returns:
            record (``dict``): Inserted record

        """
        return self.insert_in_table(self.table_name, fields, typecast=typecast)

    def batch_insert(self, records, typecast=False):
        """
        Calls :any:`insert` repetitively, following set API Rate Limit (5/sec)
        To change the rate limit use ``airtable.API_LIMIT = 0.2``
        (5 per second)

        >>> records = [{'Name': 'John'}, {'Name': 'Marc'}]
        >>> airtable.batch_insert(records)

        Args:
            records(``list``): Records to insert
            typecast(``boolean``): Automatic data conversion from string values.

        Returns:
            records (``list``): list of added records

        """
        return self.batch_insert_in_table(self.table_name, records, typecast=typecast)

    def update(self, record_id, fields, typecast=False):
        """
        Updates a record by its record id.
        Only Fields passed are updated, the rest are left as is.

        >>> record = airtable.match('Employee Id', 'DD13332454')
        >>> fields = {'Status': 'Fired'}
        >>> airtable.update(record['id'], fields)

        Args:
            record_id(``str``): Id of Record to update
            fields(``dict``): Fields to update.
                Must be dictionary with Column names as Key
            typecast(``boolean``): Automatic data conversion from string values.

        Returns:
            record (``dict``): Updated record
        """
        return self.update_in_table(self.table_name, record_id, fields, typecast=typecast)

    def update_by_field(
        self, field_name, field_value, fields, typecast=False, **options
    ):
        """
        Updates the first record to match field name and value.
        Only Fields passed are updated, the rest are left as is.

        >>> record = {'Name': 'John', 'Tel': '540-255-5522'}
        >>> airtable.update_by_field('Name', 'John', record)

        Args:
            field_name (``str``): Name of field to match (column name).
            field_value (``str``): Value of field to match.
            fields(``dict``): Fields to update.
                Must be dictionary with Column names as Key
            typecast(``boolean``): Automatic data conversion from string values.

        Keyword Args:
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParam`.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending. See :any:`SortParam`.

        Returns:
            record (``dict``): Updated record
        """
        return self.update_by_field_in_table(self.table_name, field_name, field_value, fields, typecast=typecast, **options)

    def replace(self, record_id, fields, typecast=False):
        """
        Replaces a record by its record id.
        All Fields are updated to match the new ``fields`` provided.
        If a field is not included in ``fields``, value will bet set to null.
        To update only selected fields, use :any:`update`.

        >>> record = airtable.match('Seat Number', '22A')
        >>> fields = {'PassangerName': 'Mike', 'Passport': 'YASD232-23'}
        >>> airtable.replace(record['id'], fields)

        Args:
            record_id(``str``): Id of Record to update
            fields(``dict``): Fields to replace with.
                Must be dictionary with Column names as Key.
            typecast(``boolean``): Automatic data conversion from string values.

        Returns:
            record (``dict``): New record
        """
        return self.replace_in_table(self.table_name, record_id, fields, typecast=typecast)

    def replace_by_field(
        self, field_name, field_value, fields, typecast=False, **options
    ):
        """
        Replaces the first record to match field name and value.
        All Fields are updated to match the new ``fields`` provided.
        If a field is not included in ``fields``, value will bet set to null.
        To update only selected fields, use :any:`update`.

        Args:
            field_name (``str``): Name of field to match (column name).
            field_value (``str``): Value of field to match.
            fields(``dict``): Fields to replace with.
                Must be dictionary with Column names as Key.
            typecast(``boolean``): Automatic data conversion from string values.

        Keyword Args:
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParam`.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending. See :any:`SortParam`.

        Returns:
            record (``dict``): New record
        """
        return self.replace_by_field_in_table(
            self.table_name, field_name, field_value, fields, typecast=typecast, **options
        )

    def delete(self, record_id):
        """
        Deletes a record by its id

        >>> record = airtable.match('Employee Id', 'DD13332454')
        >>> airtable.delete(record['id'])

        Args:
            record_id(``str``): Airtable record id

        Returns:
            record (``dict``): Deleted Record
        """
        return self.delete_in_table(self.table_name, record_id)

    def delete_by_field(self, field_name, field_value, **options):
        """
        Deletes first record  to match provided ``field_name`` and
        ``field_value``.

        >>> record = airtable.delete_by_field('Employee Id', 'DD13332454')

        Args:
            field_name (``str``): Name of field to match (column name).
            field_value (``str``): Value of field to match.

        Keyword Args:
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParam`.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending. See :any:`SortParam`.

        Returns:
            record (``dict``): Deleted Record
        """

        return self.delete_by_field_in_table(self.table_name, field_name, field_value, **options)

    def batch_delete(self, record_ids):
        """
        Calls :any:`delete` repetitively, following set API Rate Limit (5/sec)
        To change the rate limit set value of ``airtable.API_LIMIT`` to
        the time in seconds it should sleep before calling the function again.

        >>> record_ids = ['recwPQIfs4wKPyc9D', 'recwDxIfs3wDPyc3F']
        >>> airtable.batch_delete(records_ids)

        Args:
            records(``list``): Record Ids to delete

        Returns:
            records(``list``): list of records deleted

        """
        return self.batch_delete_in_table(self.table_name, record_ids)

    def mirror(self, records, **options):
        """
        Deletes all records on table or view and replaces with records.

        >>> records = [{'Name': 'John'}, {'Name': 'Marc'}]

        >>> record = airtable.mirror(records)

        If view options are provided, only records visible on that view will
        be deleted.

        >>> record = airtable.mirror(records, view='View')
        ([{'id': 'recwPQIfs4wKPyc9D', ... }], [{'deleted': True, ... }])

        Args:
            records(``list``): Records to insert

        Keyword Args:
            max_records (``int``, optional): The maximum total number of
                records that will be returned. See :any:`MaxRecordsParam`
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParam`.

        Returns:
            records (``tuple``): (new_records, deleted_records)
        """

        return self.mirror_in_table(self.table_name, records, **options)

    def __repr__(self):
        return "<Airtable table:{}>".format(self.table_name)
