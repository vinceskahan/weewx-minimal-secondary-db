#
# This attempts to create the most minimalist extension
# creating a secondary db possible, as a template for future
# similar extensions.
#
# This is derived from pmon.py in 4.0b1 as a starting point.
#

import weewx
import weedb
import weeutil.weeutil
from weewx.engine import StdService

import os
import syslog
import time

VERSION = "0.2"

#------- standard weewx logging wrappers -----

def logmsg(level, msg):
    syslog.syslog(level, 'dbexample: %s' % msg)

def logdbg(msg):
    logmsg(syslog.LOG_DEBUG, msg)

def loginf(msg):
    logmsg(syslog.LOG_INFO, msg)

def logerr(msg):
    logmsg(syslog.LOG_ERR, msg)


#------- custom schema -------
# we'll add one custom element to store in the db

schema = [
    ('dateTime', 'INTEGER NOT NULL PRIMARY KEY'),
    ('usUnits', 'INTEGER NOT NULL'),
    ('interval', 'INTEGER NOT NULL'),
    ('myDateTime', 'INTEGER'),
]


#------ the custom service itself ------

class MyService(StdService):

    def __init__(self, engine, config_dict):
        super(MyService, self).__init__(engine, config_dict)

        d = config_dict.get('dbexample', {})
        self.process = d.get('process', 'weewxd')
        self.max_age = weeutil.weeutil.to_int(d.get('max_age', 2592000))

        # get the database parameters we need to function
        binding = d.get('data_binding', 'dbexample_binding')

        self.dbm = self.engine.db_binder.get_manager(data_binding=binding,
                                                     initialize=True)

        # be sure database matches the schema we have
        dbcol = self.dbm.connection.columnsOf(self.dbm.table_name)
        dbm_dict = weewx.manager.get_manager_dict_from_config(config_dict, binding)
        memcol = [x[0] for x in dbm_dict['schema']]
        if dbcol != memcol:
            raise Exception('dbexample schema mismatch: %s != %s' % (dbcol, memcol))

        self.last_ts = None
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

    def shutDown(self):
        try:
            self.dbm.close()
        except weedb.DatabaseError:
            pass

    def new_archive_record(self, event):
        """save data to database then prune old records as needed"""
        now = int(time.time() + 0.5)
        delta = now - event.record['dateTime']
        if delta > event.record['interval'] * 60:
            logdbg("Skipping record: time difference %s too big" % delta)
            return
        if self.last_ts is not None:
            self.save_data(self.get_data(now, self.last_ts))
        self.last_ts = now
        if self.max_age is not None:
            self.prune_data(now - self.max_age)

    def save_data(self, record):
        """save data to database"""
        self.dbm.addRecord(record)

    def prune_data(self, ts):
        """delete records with dateTime older than ts"""
        sql = "delete from %s where dateTime < %d" % (self.dbm.table_name, ts)
        self.dbm.getSql(sql)
        try:
            # sqlite databases need some help to stay small
            self.dbm.getSql('vacuum')
        except weedb.DatabaseError:
            pass

    def get_data(self, now_ts, last_ts):
        record = dict()
        record['dateTime'] = now_ts
        record['usUnits'] = weewx.METRIC
        record['interval'] = int((now_ts - last_ts) / 60)

        # here we save secs-since-epoch into our custom element
        # just to show that the custom field gets populated by weewx
        record['myDateTime'] = now_ts

        return record

# what follows is a basic unit test of this module.  to run the test:
#
# cd /home/weewx
# PYTHONPATH=bin python bin/user/dbexample.py
#
if __name__ == "__main__":
    from weewx.engine import StdEngine
    config = {
        'Station': {
            'station_type': 'Simulator',
            'altitude': [0, 'foot'],
            'latitude': 0,
            'longitude': 0},
        'Simulator': {
            'driver': 'weewx.drivers.simulator',
            'mode': 'simulator'},
        'MyService': {
            'data_binding': 'dbexample_binding',
            'process': 'weewxd'},
        'DataBindings': {
            'dbexample_binding': {
                'database': 'dbexample_sqlite',
                'manager': 'weewx.manager.DaySummaryManager',
                'table_name': 'archive',
                'schema': 'user.dbexample.schema'}},
        'Databases': {
            'dbexample_sqlite': {
                'database_name': 'dbexample.sdb',
                'database_type': 'SQLite'}},
        'DatabaseTypes': {
            'SQLite': {
                'driver': 'weedb.sqlite',
                'SQLITE_ROOT': '/var/tmp'}},
        'Engine': {
            'Services': {
                'process_services': 'user.dbexample.MyService'}
            }
        }
    eng = StdEngine(config)
    svc = MyService(eng, config)

    nowts = lastts = int(time.time())
    rec = svc.get_data(nowts, lastts)
    print(rec)

    time.sleep(5)
    nowts = int(time.time())
    rec = svc.get_data(nowts, lastts)
    print(rec)

    time.sleep(5)
    lastts = nowts
    nowts = int(time.time())
    rec = svc.get_data(nowts, lastts)
    print(rec)

    # it would be good to write these records to the tmp db
    # and then do something like a 'select * from archive'
    # to see that they were written out

    os.remove('/var/tmp/dbexample.sdb')


#----- that's all folks -----

