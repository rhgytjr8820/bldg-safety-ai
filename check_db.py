from app import create_app
from sqlalchemy import inspect
from app.extensions import db

app = create_app()
with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    for table in tables:
        print(f"=== {table} ===")
        for col in inspector.get_columns(table):
            nullable = "NULL" if col["nullable"] else "NOT NULL"
            col_name = col["name"]
            col_type = str(col["type"])
            print(f"  {col_name:20s} {col_type:20s} {nullable}")
        fks = inspector.get_foreign_keys(table)
        if fks:
            for fk in fks:
                print(f"  [FK] {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
        print()

    # 데이터 확인
    from app.models.role import Role
    from app.models.user import User
    from app.models.device import JetsonDevice

    print("=== roles 데이터 ===")
    for r in Role.query.all():
        print(f"  id={r.id}, name={r.role_name}, level={r.level}")

    print("\n=== users 데이터 ===")
    for u in User.query.all():
        print(f"  id={u.id}, email={u.email}, name={u.name}, role_id={u.role_id}")

    print("\n=== jetson_devices 데이터 ===")
    devices = JetsonDevice.query.all()
    if devices:
        for d in devices:
            print(f"  id={d.device_id}, mac={d.mac_address}, name={d.device_name}")
    else:
        print("  (empty)")
