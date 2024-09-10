import pygrib
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import numpy as np
import shapefile as shp
from matplotlib.collections import LineCollection

file_path = 'WRF_cpt_07KM_SU_2024082112_2024082609.grib2'
grbs = pygrib.open(file_path)
grb = grbs.select(name='2 metre temperature')[0]
data = grb.values - 273.15
lat, lon = grb.latlons()
grbs.close()
levels = np.arange(-3, 16, 1)
plt.figure(figsize=(10, 8))
m = Basemap(projection='cyl', llcrnrlat=lat.min(), urcrnrlat=lat.max(), llcrnrlon=lon.min(), urcrnrlon=lon.max(), resolution='l')
m.drawcoastlines()
m.drawcountries()
m.drawstates()
contour = m.contourf(lon, lat, data, levels=levels, cmap='jet', extend='both')
cbar = m.colorbar(contour, ticks=levels, label='Temperatura a 2 metros (°C)')
cbar.ax.set_yticklabels([f'{int(level)}' for level in levels])
plt.title('Temperatura 26/08/2024 6h')
output_path = '2m_temperatura.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
plt.show()
