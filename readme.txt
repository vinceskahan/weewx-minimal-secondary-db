


Intent is to provide a template starting point for a minimal extension
that writes to a secondary sqlite3 database.

To test:
   PYTHONPATH=/home/weewx/bin python3 bin/user/dbexample.py


=================================================
 MANUAL INSTALLATION
   define the data binding pointing to the db
   define the db and its type
   append the service to process_services  
=================================================

[DataBindings]
    
    [[dbexample_binding]]
        database = dbexample_sqlite
        table_name = archive
        manager = weewx.manager.DaySummaryManager
        schema = user.dbexample.schema

[Databases]
    
    [[dbexample_sqlite]]
        database_name = dbexample.sdb
        database_type = SQLite

[Engine]
    
    [[Services]]
        process_services = [....previous entries...] , user.dbexample.MyService
