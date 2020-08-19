#!/usr/bin/python
import numpy as np
import collections
from datetime import datetime
import re
import netcdf_read_write as rwr

data = collections.namedtuple('data', ['filepaths', 'dates_correct', 'date_deltas',  'xvalues', 'yvalues', 'zvalues'])

def reader(filepathslist):
    """
    This function takes in a list of filepaths that each contain a 2d array of data, effectively taking
    in a cuboid of data. It splits and stores this data in a named tuple which is returned. This can then be used
    to extract key pieces of information.
    It functions on GMTSAR grd files in radar coordinates. 
    """
    filepaths  = []
    dates_correct , date_deltas = [], []
    xvalues, yvalues, zvalues = [], [], []
    for i in range(len(filepathslist)):
        print(filepathslist[i])
        # Establish timing and filepath information
        filepaths.append(filepathslist[i])
        datesplit = filepathslist[i].split('/')[-2]  # example: 2015157_2018177_unwrap.grd
        date_new = datesplit.replace(datesplit[0:7], str(int(datesplit[0:7]) + 1))
        date_new = date_new.replace(date_new[8:15], str(int(date_new[8:15]) + 1))  # adding 1 to the date because 000 = January 1
        dates_correct.append(date_new[0:15])  # example: 2015158_2018178
        delta = abs(datetime.strptime(dates_correct[i][0:7], '%Y%j') - datetime.strptime(dates_correct[i][8:15], '%Y%j'))  # timedelta object
        date_deltas.append(delta.days/365.24)  # in years. Is that a good idea? 

        # Read in the data
        try: 
            xdata, ydata, zdata = rwr.read_grd_xyz(filepathslist[i])  # a NETCDF3 file
        except TypeError:
            xdata, ydata, zdata = rwr.read_netcdf4_xyz(filepathslist[i])  # a NETCDF4 file

        xvalues=xdata
        yvalues=ydata
        zvalues.append(zdata)
        if i == round(len(filepathslist)/2):
            print('halfway done reading files...')

    mydata = data(filepaths=np.array(filepaths), dates_correct=np.array(dates_correct), 
        date_deltas=np.array(date_deltas), xvalues=np.array(xvalues), yvalues=np.array(yvalues), zvalues=np.array(zvalues))
    return mydata


def reader_from_ts(filepathslist, xvar="x", yvar="y", zvar="z"):
    """ 
    This function makes a tuple of grids in timesteps
    It can read in radar coords or geocoded coords, depending on the use of xvar, yvar
    """
    filepaths  = [];  zvalues = [];
    dates_correct, date_deltas=[], [];
    for i in range(len(filepathslist)):
        print(filepathslist[i])
        # Establish timing and filepath information
        filepaths.append(filepathslist[i]);
        datestr = filepathslist[i].split('/')[-1][0:8];
        dates_correct.append(datetime.strptime(datestr,"%Y%m%d"));
        date_deltas.append(0);  # placeholder because these are timesteps, not intfs
        # Read in the data
        [xvalues, yvalues, zdata] = rwr.read_any_grd_variables(filepathslist[i],xvar,yvar,zvar);  # can read netcdf3 or netcdf4
        zvalues.append(zdata);
        if i == round(len(filepathslist)/2):
            print('halfway done reading files...');
    mydata = data(filepaths=np.array(filepaths), dates_correct=np.array(dates_correct), 
        date_deltas=np.array(date_deltas), xvalues=np.array(xvalues), yvalues=np.array(yvalues), zvalues=np.array(zvalues)); 
    return mydata;


def reader_simple_format(file_names):
    """
    An earlier reading function, works fast, useful for things like coherence statistics
    """
    [xdata,ydata] = netcdf_read_write.read_grd_xy(file_names[0]);
    data_all=[];
    for ifile in file_names:  # this happens to be in date order on my mac
        data = netcdf_read_write.read_grd(ifile);
        data_all.append(data);
    date_pairs=[];
    for name in file_names:
        pairname=name.split('/')[-2][0:15];
        date_pairs.append(pairname);  # returning something like '2016292_2016316' for each intf
        print(pairname)
    return [xdata, ydata, data_all, date_pairs];


def reader_isce(filepathslist, band=1):
    import isce_read_write

    """
    This function takes in a list of filepaths that each contain a 2d array of data, effectively taking
    in a cuboid of data. It splits and stores this data in a named tuple which is returned. This can then be used
    to extract key pieces of information. It reads in ISCE format. 
    """

    filepaths  = []
    dates_correct , date_deltas = [], []
    xvalues, yvalues, zvalues = [], [], []
    for i in range(len(filepathslist)):
        filepaths.append(filepathslist[i])
        # In the case of ISCE, we have the dates in YYYYMMDD_YYYYMMDD format somewhere within the filepath (maybe multiple times). We take the first. 
        datesplit = re.findall(r"\d\d\d\d\d\d\d\d_\d\d\d\d\d\d\d\d", filepathslist[i])[0]; #  example: 20100402_20140304
        date1 = datetime.strptime(datesplit[0:8],"%Y%m%d");
        date2 = datetime.strptime(datesplit[9:17],"%Y%m%d");
        datestr_julian=datetime.strftime(date1,"%Y%j")+"_"+datetime.strftime(date2,"%Y%j");  # in order to maintain consistency with GMTSAR formats
        dates_correct.append(datestr_julian)  # example: 2015158_2018178
        delta = abs(date1-date2)
        date_deltas.append(delta.days/365.24)  # in years. 

        zdata = isce_read_write.read_scalar_data(filepathslist[i], band, flush_zeros=False);  # NOTE: For unwrapped files, this will be band=2
        # flush_zeros=False preserves the zeros in the input datasets. Added April 9 2020. Hope it doesn't break anything else. 
        xvalues=range(0,np.shape(zdata)[1]);
        yvalues=range(0,np.shape(zdata)[0]);
        zvalues.append(zdata)
        if i == round(len(filepathslist)/2):
            print('halfway done reading files...')

    mydata = data(filepaths=np.array(filepaths), dates_correct=np.array(dates_correct), 
        date_deltas=np.array(date_deltas), xvalues=np.array(xvalues), yvalues=np.array(yvalues), zvalues=np.array(zvalues))

    return mydata; 