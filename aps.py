# Atmospheric Phase Screen method of Tymofyeyeva and Fialko, 2015


import numpy as np 
import matplotlib.pyplot as plt 
from subprocess import call 
import glob, sys
import datetime as dt 
import netcdf_read_write


def main_function(staging_directory, out_dir):
	[file_names, width_of_stencil] = configure(staging_directory, out_dir);
	[xdata, ydata, data_all, dates, date_pairs] = inputs(file_names);
	compute(xdata, ydata, data_all, dates, date_pairs, width_of_stencil, out_dir);
	return;

# ------------- CONFIGURE ------------ # 
def configure(staging_directory, out_dir):
	width_of_stencil = 25;   # in days.  

	# Setting up the input and output directories. 
	file_names=glob.glob(staging_directory+"/*_*_unwrap.grd");
	file_names=sorted(file_names);
	print("Performing APS on files in %s " % staging_directory);
	if len(file_names)==0:
		print("Error! No files matching search pattern within "+staging_directory); sys.exit(1);
	call(['mkdir','-p',out_dir],shell=False);
	return [file_names, width_of_stencil];


# ------------- INPUTS ------------ # 
def inputs(file_names):
	[xdata,ydata] = netcdf_read_write.read_grd_xy(file_names[0]);
	data_all=[];
	for ifile in file_names:  # this happens to be in date order on my mac
		data = netcdf_read_write.read_grd(ifile);
		data_all.append(data);
	date_pairs=[];
	dates=[];
	for name in file_names:
		pairname=name.split('/')[-1][0:15];
		date_pairs.append(pairname);  # returning something like '2016292_2016316' for each intf
		splitname=pairname.split('_');
		dates.append(splitname[0])
		dates.append(splitname[1])
	dates=list(set(dates));
	dates=sorted(dates);
	print(dates);
	return [xdata, ydata, data_all, dates, date_pairs];

# ----------- COMPUTE ------------- #

def form_APS_pairs(date_pairs, mydate, containing, width_of_stencil):
	# Date pairs: a global list of available interferograms (in order).
	# containing: a small list of interferograms that contain the image of interest
	# width_of_stencil: the number of days we tolerate in stencils

	pairlist = [];

	print("images that contain "+mydate+":")
	print(containing);
	for item in containing: # for each interferogram containing the main image...
		image1=item.split('_')[0];
		image2=item.split('_')[1];
		if image1==mydate:
			continue;
		dt1 = dt.datetime.strptime(image1,"%Y%j");
		dt2 = dt.datetime.strptime(image2,"%Y%j");
		imwidth = (dt2 - dt1).days;
		if abs(imwidth)<width_of_stencil:  # for each valid interferogram that lands on the master image
			# See if there is a pair in the stack. Does it exist? 

			item_potential_match = dt.datetime.strftime(dt2+dt.timedelta(days=abs(imwidth)),"%Y%j");
			item_potential_pair = image2+'_'+item_potential_match;

			if item_potential_pair in containing:
				pair1=item;
				pair2=item_potential_pair;
				#print("%s found matching %s" % (item_potential_pair, item));
				index1=date_pairs.index(pair1);
				index2=date_pairs.index(pair2);
				pairlist.append([index1, index2])

	print(pairlist);
	# Example of pairlist: [[63,65],[62,66]], where the numbers are the indeces of paired interferograms used for APS construction

	return pairlist; 


def compute_one_image(dates, date_pairs, data_all, width_of_stencil, mydate, out_dir):

	containing = [item for item in date_pairs if mydate in item];  # which interferograms contain the image of interest? 
	zdim, rowdim, coldim = np.shape(data_all);

	# A list of valid interferogram pairs by index in the stack, which we use for making APS
	pairlist = form_APS_pairs(date_pairs, mydate, containing, width_of_stencil);
	if len(pairlist)==0:
		print("ERROR! No valid APS stencils were detected in the stack for image %s" % mydate)
		my_aps=np.zeros((rowdim,coldim));
		loopcheck=np.zeros((rowdim,coldim));
		return [0,0,0,0,0,0,0];


	my_aps=np.zeros((rowdim,coldim));
	intf1_corrected=np.zeros((rowdim,coldim));
	intf2_corrected=np.zeros((rowdim,coldim));
	loopcheck=np.zeros((rowdim,coldim));
	myaps_1darray=[];

	for i in range(rowdim):
		for j in range(coldim):  # for each pixel...

			aps_temp_sum=0;
			pair_counter=0;

			for k in range(len(pairlist)):
				intf1_index=pairlist[k][0];
				intf2_index=pairlist[k][1];
				if ~np.isnan(data_all[intf1_index][i][j]) and ~np.isnan(data_all[intf2_index][i][j]):  
				# if both interferograms are numbers, then add to APS estimate. 
					pair_counter=pair_counter+1;
					aps_temp_sum = aps_temp_sum + (data_all[intf1_index][i][j] - data_all[intf2_index][i][j]);
			
			if pair_counter>0:
				my_aps[i][j]=(1.0/(2*pair_counter))*aps_temp_sum;
				myaps_1darray.append(my_aps[i][j]);
			else:
				my_aps[i][j]=np.nan;
			loopcheck[i][j]=pair_counter;

			intf1_corrected[i][j]=data_all[intf1_index][i][j] - my_aps[i][j];
			intf2_corrected[i][j]=data_all[intf2_index][i][j] + my_aps[i][j];


	print(mydate);
	ANC=compute_ANC(myaps_1darray);
	print("ANC: %.2f" % ANC);

	view_one_image(data_all, date_pairs, mydate, my_aps, loopcheck, intf1_index, intf1_corrected, intf2_index, intf2_corrected, ANC, out_dir);

	return [my_aps, intf1_index, intf1_corrected, intf2_index, intf2_corrected, loopcheck, ANC];


def compute_ANC(myaps):
	# myaps = 1d array of numeric values
	# A scaled RMS of the atmospheric phase screen.
	normalizer=10;
	M=len(myaps);
	abar = np.mean(myaps);
	res_sq_array = [(a-abar)*(a-abar) for a in myaps];
	ANC = np.sqrt((1.0/M) * np.sum(res_sq_array) );
	return ANC;


def compute(xdata, ydata, data_all, dates, date_pairs, width_of_stencil, out_dir):

	# Automated selection of dates and interferograms for APS construction
	#mydate=dates[15];

	for mydate in dates:

		[my_aps, intf1_index, intf1_corrected, intf2_index, intf2_corrected, loopcheck, ANC] = compute_one_image(dates, date_pairs, data_all, width_of_stencil, mydate, out_dir);

	return;


# ----------- OUTPUTS ------------- # 
def view_one_image(data_all, date_pairs, mydate, my_aps, loopcheck, intf1_index, intf1_corrected, intf2_index, intf2_corrected, ANC, out_dir):

	vmin=-20;
	vmax=20;

	plt.figure();
	plt.subplot(2,3,1);
	plt.imshow(data_all[intf1_index],cmap='hsv',vmin=vmin, vmax=vmax);
	plt.title(date_pairs[intf1_index]);
	plt.gca().invert_yaxis()
	plt.gca().invert_xaxis()
	plt.gca().get_xaxis().set_ticks([]);
	plt.gca().get_yaxis().set_ticks([])

	plt.subplot(2,3,2)
	plt.imshow(data_all[intf2_index],cmap='hsv', vmin=vmin, vmax=vmax);
	plt.title(date_pairs[intf2_index]);
	plt.gca().invert_yaxis()
	plt.gca().invert_xaxis()
	plt.gca().get_xaxis().set_ticks([]);
	plt.gca().get_yaxis().set_ticks([])

	plt.subplot(2,3,3);
	plt.imshow(my_aps, cmap='hsv',vmin=vmin, vmax=vmax);
	plt.title('ANC: %.2f' % ANC)
	plt.gca().invert_yaxis()
	plt.gca().invert_xaxis()
	plt.gca().get_xaxis().set_ticks([]);
	plt.gca().get_yaxis().set_ticks([])

	plt.subplot(2,3,4);
	plt.imshow(intf1_corrected,cmap='hsv',vmin=vmin, vmax=vmax);
	plt.title('intf1_corr');
	plt.gca().invert_yaxis()
	plt.gca().invert_xaxis()
	plt.gca().get_xaxis().set_ticks([]);
	plt.gca().get_yaxis().set_ticks([])

	plt.subplot(2,3,5)
	plt.imshow(intf2_corrected,cmap='hsv', vmin=vmin, vmax=vmax);
	plt.title('intf2_corr');
	plt.gca().invert_yaxis()
	plt.gca().invert_xaxis()
	plt.gca().get_xaxis().set_ticks([]);
	plt.gca().get_yaxis().set_ticks([])

	plt.subplot(2,3,6)
	plt.imshow(loopcheck,cmap='jet',vmin=-0.1, vmax=2.1);
	plt.title('loops for '+mydate);
	plt.gca().invert_yaxis()
	plt.gca().invert_xaxis()
	plt.gca().get_xaxis().set_ticks([]);
	plt.gca().get_yaxis().set_ticks([])
	plt.savefig(out_dir+'/initialmask_'+mydate+'.png');
	plt.close();
	return;
