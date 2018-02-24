# Sentinel Utilities

from subprocess import call
import os
import sys
import glob
import datetime
import matplotlib.pyplot as plt 
import numpy as np


def get_all_xml_names(directory, polarization, swath):
    pathname1=directory+"/*-vv-*-00"+swath+".xml";
    pathname2=directory+"/*-vv-*-00"+str(int(swath)+3)+".xml";
    list_of_images_temp=glob.glob(pathname1)+glob.glob(pathname2);
    list_of_images=[]
    for item in list_of_images_temp:
        list_of_images.append(item[:])
    return list_of_images;

def get_manifest_safe_names(directory):
    mansafe=glob.glob(directory+'/manifest.safe');
    return mansafe;

def get_all_tiff_names(directory, polarization, swath):
    pathname1=directory+"/*-vv-*-00"+swath+".tiff";
    pathname2=directory+"/*-vv-*-00"+str(int(swath)+3)+".tiff";
    list_of_images_temp=glob.glob(pathname1)+glob.glob(pathname2);
    list_of_images=[]
    for item in list_of_images_temp:
        list_of_images.append(item[:])
    return list_of_images;


def get_previous_and_following_day(datestring):
    """ This is a function that takes a date like 20160827 and generates 
    [20160826, 20160828]: the day before and the day after the date in question. """
    year=int(datestring[0:4]);
    month=int(datestring[4:6]);
    day=int(datestring[6:8]);
    mydate=datetime.date(year, month, day);
    tomorrow =mydate + datetime.timedelta(days=1);
    yesterday=mydate - datetime.timedelta(days=1);
    previous_day=pad_string_zeros(yesterday.year)+pad_string_zeros(yesterday.month)+pad_string_zeros(yesterday.day);
    following_day=pad_string_zeros(tomorrow.year)+pad_string_zeros(tomorrow.month)+pad_string_zeros(tomorrow.day);
    return [previous_day, following_day];

def get_date_from_xml(xml_name):
    """
    xml file has name like s1a-iw1-slc-vv-20150121t134413-20150121t134424-004270-005317-001.xml
    We want to return 20150121. 
    """
    xml_name=xml_name.split('/')[-1];
    mydate=xml_name[15:23];
    return mydate;

def pad_string_zeros(num):
    if num<10:
        numstring="0"+str(num);
    else:
        numstring=str(num);
    return numstring;


# NOTE: Eventually I will have to add a functionality to distinguish between S1A and S1B. 
def get_eof_from_xml(xml_name, eof_dir): 
    """ This returns something like S1A_OPER_AUX_POEORB_OPOD_20160930T122957_V20160909T225943_20160911T005943.EOF. 
    """
    mydate=get_date_from_xml(xml_name);
    [previous_day,following_day]=get_previous_and_following_day(mydate);
    eof_name=glob.glob(eof_dir+"/*"+previous_day+"*"+following_day+"*.EOF"); 
    if eof_name==[]:
        print "ERROR: did not find any EOF files matching the pattern "+eof_dir+"/*"+previous_day+"*"+following_day+"*.EOF";
        print "Exiting..."
        sys.exit(1);
    else:
        eof_name=eof_name[0];
    return eof_name;


def get_eof_from_date_sat(mydate, sat, eof_dir):
    """ This returns something like S1A_OPER_AUX_POEORB_OPOD_20160930T122957_V20160909T225943_20160911T005943.EOF.
        It takes something like 20171204, s1a, eof_dir 
    """
    [previous_day,following_day]=get_previous_and_following_day(mydate);
    eof_name=glob.glob(eof_dir+"/"+sat.upper()+"*"+previous_day+"*"+following_day+"*.EOF"); 
    if eof_name==[]:
        print "ERROR: did not find any EOF files matching the pattern "+eof_dir+"/"+sat.upper()+"*"+previous_day+"*"+following_day+"*.EOF";
        print "Exiting..."
        sys.exit(1);
    else:
        eof_name=eof_name[0];
    return eof_name;


def make_data_in(polarization, swath, master_date="00000000"):
    """
    data.in is a reference table that links the xml file with the correct orbit file.
    """
    list_of_images=get_all_xml_names("raw_orig",polarization,swath);
    outfile=open("data.in",'w');
    if master_date=="00000000":
        for item in list_of_images:
            item=item.split("/")[-1];  # getting rid of the directory
            eof_name=get_eof_from_xml(item,"raw_orig");
            outfile.write(item[:-4]+":"+eof_name.split("/")[-1]+"\n");
    else:
        # write the master date first. 
        for item in list_of_images:
            mydate=get_date_from_xml(item);
            if mydate==master_date:
                item=item.split("/")[-1];  # getting rid of the directory
                eof_name=get_eof_from_xml(item,"raw_orig");
                outfile.write(item[:-4]+":"+eof_name.split("/")[-1]+"\n");
        # then write the other dates. 
        for item in list_of_images:
            mydate = get_date_from_xml(item);
            if mydate != master_date:
                item=item.split("/")[-1];  # getting rid of the directory
                eof_name=get_eof_from_xml(item,"raw_orig");
                outfile.write(item[:-4]+":"+eof_name.split("/")[-1]+"\n");
    outfile.close();
    print "data.in successfully printed."
    return;


# after running the baseline calculation from the first pre_proc_batch, choose a new master that is close to the median baseline and timespan.
def choose_master_image():    
    # load baseline table
    baselineFile = np.genfromtxt('raw/baseline_table.dat',dtype=str)
    time = baselineFile[:,1].astype(float)
    baseline = baselineFile[:,4].astype(float)
    shortform_names = baselineFile[:,0].astype(str);
 
    #GMTSAR (currently) guarantees that this file has the same order of lines as baseline_table.dat.
    dataDotIn=np.genfromtxt('raw/data.in',dtype='str').tolist()
    print dataDotIn;    

    # calculate shortest distance from median to scenes
    consider_time=True
    if consider_time:
        time_baseline_scale=1 #arbitrary scaling factor, units of (meters/day)
        sceneDistance = np.sqrt(((time-np.median(time))/time_baseline_scale)**2 + (baseline-np.median(baseline))**2)
    else:
        sceneDistance = np.sqrt((baseline-np.median(baseline))**2)
    
    minID=np.argmin(sceneDistance)
    masterID=dataDotIn[minID]    
   
    # put masterId in the first line of data.in
    dataDotIn.pop(dataDotIn.index(masterID))
    dataDotIn.insert(0,masterID)
    master_shortform = shortform_names[minID];  # because GMTSAR initially puts the baseline_table and data.in in the same order. 
    
    os.rename('raw/data.in','raw/data.in.old')
    np.savetxt('raw/data.in',dataDotIn,fmt='%s')
    np.savetxt('data.in',dataDotIn,fmt='%s')
    return master_shortform

def write_super_master_batch_config(masterid):
    ifile=open('batch.config','r');
    ofile=open('batch.config.new','w');
    for line in ifile:
        if 'master_image' in line:
            ofile.write('master_image = '+masterid+'\n');
        else:        
            ofile.write(line);
    ifile.close();
    ofile.close();
    call(['mv','batch.config.new','batch.config'],shell=False);
    print "Writing master_image into batch.config";
    return;


def get_small_baseline_subsets(stems, tbaseline, xbaseline, tbaseline_max, xbaseline_max):
    """ Grab all the pairs that are below the critical baselines in space and time. 
    Return format is a list of strings like 'S1A20150310_ALL_F1:S1A20150403_ALL_F1'. 
    You can adjust this if you have specific processing needs. 
    """
    nacq=len(stems);
    intf_pairs=[];
    for i in range(0,nacq):
        for j in range(i+1,nacq):
            if abs(tbaseline[i]-tbaseline[j]) < tbaseline_max:
                if abs(xbaseline[i]-xbaseline[j]) < xbaseline_max:
                    img1_stem=stems[i];
                    img2_stem=stems[j];
                    img1_time=int(img1_stem[3:11]);
                    img2_time=int(img2_stem[3:11]);
                    if img1_time<img2_time:  # if the images are listed in chronological order 
                        intf_pairs.append(stems[i]+":"+stems[j]);
                    else:                    # if the images are in reverse chronological order
                        intf_pairs.append(stems[j]+":"+stems[i]);
    print "Returning "+str(len(intf_pairs))+" of "+str(nacq*(nacq-1)/2)+" possible interferograms to compute. "
    # The total number of pairs is (n*n-1)/2.  How many of them fit our small baseline criterion?
    return intf_pairs;



def make_network_plot(intf_pairs,stems,tbaseline,xbaseline):
    plt.figure();
    for item in intf_pairs:
        scene1=item[0:18];
        scene2=item[19:];
        for x in range(len(stems)):
            if stems[x]==scene1:
                xstart=xbaseline[x];
                tstart=tbaseline[x]-2000000;
            if stems[x]==scene2:
                xend=xbaseline[x];
                tend=tbaseline[x]-2000000;
        plt.plot(tstart, xstart,'.b');
        plt.plot(tend, xend,'.b');
        plt.plot([tstart,tend],[xstart,xend],'b');
    plt.xlabel("Year-day");
    plt.ylabel("Baseline (m)");
    plt.title("Network Geometry");
    plt.savefig("Network_Geometry.eps");
    plt.close();
    return();

