import time
from novas import compat as novas
from novas.compat import eph_manager

def getOwlt(t):
    '''Uses novas module to compute One Way Light Time at given UTC time.'''
    utc_time = time.strptime(t, "%Y-%m-%dT%H:%M:%S.%fZ")
    jd_start, jd_end, number = eph_manager.ephem_open("/Library/Python/2.7/site-packages/novas_de405/DE405.bin")
    jd_tt = novas.julian_date(utc_time.tm_year, utc_time.tm_mon, utc_time.tm_mday, utc_time.tm_hour)
    mars = novas.make_object(0, 4, 'Mars', None)
    ra, dec, dis = novas.astro_planet(jd_tt, mars)
    au_sec = 499.0047838061 # Light-time for one astronomical unit (AU) in seconds, from DE-405
    owlt = dis * au_sec
    return owlt
