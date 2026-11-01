# Recruitment Management System backend

This package contains the SQLAlchemy MySQL database layer, business services,
authentication and authorization, synthetic data generation, validation,
analytics, and exports. MySQL 8 is mandatory; SQLite is not supported.

Common commands from the repository root:

```powershell
python -m backend.database.migrate
python -m backend.data_generator.generator --size full --seed 20261022
python -m backend.validation.validator --size full
```
