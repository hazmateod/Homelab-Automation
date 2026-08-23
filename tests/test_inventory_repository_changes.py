from himp.database.inventory import InventoryRepository


class CapturingDatabase:
    def __init__(self):
        self.query_calls = []
        self.execute_calls = []

    def query(
        self,
        sql,
        parameters=(),
    ):
        self.query_calls.append(
            {
                "sql": sql,
                "parameters": parameters,
            }
        )

        return []

    def execute(
        self,
        sql,
        parameters=(),
    ):
        self.execute_calls.append(
            {
                "sql": sql,
                "parameters": parameters,
            }
        )


def make_repository():
    repository = object.__new__(
        InventoryRepository
    )

    repository.database = (
        CapturingDatabase()
    )

    return repository


def test_record_change_normalizes_boolean_values_to_text():
    repository = make_repository()

    repository.record_change(
        hostname="automation.server.arpa",
        change_type="UPDATED",
        field="become",
        old_value=False,
        new_value=True,
    )

    query_parameters = (
        repository.database
        .query_calls[0]["parameters"]
    )

    assert query_parameters == (
        "automation.server.arpa",
        "UPDATED",
        "become",
        "0",
        "1",
    )

    execute_parameters = (
        repository.database
        .execute_calls[0]["parameters"]
    )

    assert execute_parameters == (
        "automation.server.arpa",
        "UPDATED",
        "become",
        "0",
        "1",
    )


def test_record_change_preserves_null_values():
    repository = make_repository()

    repository.record_change(
        hostname="new-host",
        change_type="ADDED",
        field=None,
        old_value=None,
        new_value=None,
    )

    query_parameters = (
        repository.database
        .query_calls[0]["parameters"]
    )

    assert query_parameters == (
        "new-host",
        "ADDED",
        None,
        None,
        None,
    )

    execute_parameters = (
        repository.database
        .execute_calls[0]["parameters"]
    )

    assert execute_parameters == (
        "new-host",
        "ADDED",
        None,
        None,
        None,
    )
