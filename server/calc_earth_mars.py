import de421
from jplephem import Ephemeris
from novas import compat as novas
import time
import math

KM_to_AU = 6.68458712e-9
AU_SEC = 499.0047838061

def calcMag(x,y=None,z=None):
  if y is None:
    x,y,z = x[0][0], x[1][0], x[2][0]
  return math.sqrt(pow(x,2) + pow(y,2) + pow(z,2))

utc_time = time.gmtime()
jd_tt = novas.julian_date(utc_time.tm_year, utc_time.tm_mon, utc_time.tm_mday, utc_time.tm_hour)
print "Now J2000: ",jd_tt

jd_tt2 = novas.julian_date(1980, 06, 01, 0)
print "1980.06.01 J2000: ", jd_tt2

print "EPH: 1980.06.01:", "2444391.5"

eph = Ephemeris(de421)

j = jd_tt
sun = eph.position('sun', j)
mars = eph.position('mars', j)

x, y, z = eph.position('mars', 2444391.5)  # 1980.06.01

print "novas dis (AU): 2.54640013445"

m_owlt = calcMag(mars) * KM_to_AU * AU_SEC
e_owlt = calcMag(earth) * KM_to_AU * AU_SEC

print "Mars:", m_owlt
print "Earth:", e_owlt
print (calcMag(mars) - calcMag(earth))

astro = eph.earth(utc=(d_year, d_month, d_year)).observe(eph.sun)
ra, dec, distance = astro.radec
print distance.AU
