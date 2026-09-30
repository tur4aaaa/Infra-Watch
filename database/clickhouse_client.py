import clickhouse_connect

clickhouse_client = clickhouse_connect.get_client(
    host="localhost",
    port=8124,
    username="infra",
    password="infra_password",
)