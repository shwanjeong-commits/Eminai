import bootstrap  # noqa: F401

from database import connect


def main() -> None:
    with connect() as connection:
        cursor = connection.execute(
            """
            update news_items
            set analysis_status = 'queued', updated_at = current_timestamp
            where analysis_status = 'filtered'
            """
        )
        connection.commit()
        print(f"requeued_filtered={cursor.rowcount}")


if __name__ == "__main__":
    main()
