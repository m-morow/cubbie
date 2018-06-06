

# Step 1: Glob the intf_all
# Step 2: Form as many loops as possible
# Step 3: Make images of all the possible loops. 

import numpy as np 
import matplotlib.pyplot as plt 
import glob
import subprocess
import netcdf_read_write

def form_all_loops():
	loops=[]; 
	edges=[];
	nodes=[];
	directories = glob.glob("intf_all/*_*");
	for item in directories:
		edgepair=item.split('/')[-1];
		edges.append(edgepair);
		nodes.append(edgepair.split('_')[0]);
		nodes.append(edgepair.split('_')[1]);
	nodes=list(set(nodes));

	# Making a graph of nodes and edges
	startnode=[];
	endnode=[];
	for i in range(len(nodes)):
		startnode.append(nodes[i]);
		thisend=[];
		for j in range(len(nodes)):
			if nodes[i]+'_'+nodes[j] in edges or nodes[j]+'_'+nodes[i] in edges:
				thisend.append(nodes[j])
		endnode.append(thisend);

	graph=dict([ (startnode[i], endnode[i]) for i in range(len(startnode)) ]);

	# Now we find loops. 
	# Start in chronological order. Step through the main loop.  
	# Within, have a loop of connectors, and another loop of connectors. If the innermost 
	# layer comes back to the starter, then you have a loop of 3. 
	for node0 in startnode:
		for node1 in graph[node0]:
			possible_list=graph[node1];
			for node2 in possible_list:
				if node2==node0:
					continue;
				elif node0 in graph[node2]:
					loop_try = [node0, node1, node2];
					loop_try = sorted(loop_try);
					if loop_try not in loops:
						loops.append(loop_try);

	print("Number of Images (nodes): % s" % (len(startnode)));
	print("Number of Loops (circuits): % s" % (len(loops)));
	return loops;




def show_images(all_loops, loops_dir, loops_guide):
	subprocess.call(['mkdir','-p',loops_dir],shell=False);
	ofile=open(loops_dir+loops_guide,'w');
	for i in range(len(all_loops)):
		ofile.write("Loop %d: %s %s %s\n" % (i,all_loops[i][0], all_loops[i][1], all_loops[i][2]) );
	ofile.close();

	unwrapped='unwrap.grd'
	wrapped='phasefilt.grd'

	for i in range(len(all_loops)):
		edge1=all_loops[i][0]+'_'+all_loops[i][1];
		edge2=all_loops[i][1]+'_'+all_loops[i][2];
		edge3=all_loops[i][0]+'_'+all_loops[i][2];
		[xdata, ydata, z1 ] = netcdf_read_write.read_grd_xyz('intf_all/'+edge1+'/'+unwrapped);
		z2 = netcdf_read_write.read_grd('intf_all/'+edge2+'/'+unwrapped);
		z3 = netcdf_read_write.read_grd('intf_all/'+edge3+'/'+unwrapped);

		[xdata, ydata, wr_z1 ] = netcdf_read_write.read_grd_xyz('intf_all/'+edge1+'/'+wrapped);
		wr_z2 = netcdf_read_write.read_grd('intf_all/'+edge2+'/'+wrapped);
		wr_z3 = netcdf_read_write.read_grd('intf_all/'+edge3+'/'+wrapped);

		histdata=[];
		znew = np.zeros(np.shape(z1));
		errorflag=np.zeros(np.shape(z1));
		for j in range(np.shape(z1)[0]):
			for k in range(np.shape(z1)[1]):
				
				# Using equation from Heresh Fattahi's PhD thesis to isolate unwrapping errors. 
				wrapped_closure=wr_z1[j][k]+wr_z2[j][k]-wr_z3[j][k];
				offset_before_unwrapping=np.mod(wrapped_closure,2*np.pi);
				if offset_before_unwrapping>np.pi:
					offset_before_unwrapping=offset_before_unwrapping-2*np.pi;  # send it to the -pi to pi realm. 

				unwrapped_closure=z1[j][k]+z2[j][k]-z3[j][k];

				znew[j][k]=unwrapped_closure - offset_before_unwrapping;

				if ~np.isnan(znew[j][k]):
					histdata.append(znew[j][k]/np.pi);
				if znew[j][k]!=0:
					errorflag[j][k]=1;

		make_plot(xdata, ydata, znew, loops_dir+'phase_closure_'+str(i)+'.eps');
		make_histogram(histdata, loops_dir+'histogram_'+str(i)+'.eps');
		#make_plot(xdata, ydata, errorflag, loops_dir+'error_phase_closure_'+str(i)+'.eps');

	return;



def make_plot(x, y, z, plotname):
	fig = plt.figure();
	plt.imshow(z, cmap='jet',aspect=0.7);
	plt.gca().invert_yaxis()
	plt.gca().invert_xaxis()
	plt.gca().get_xaxis().set_ticks([]);
	plt.gca().get_yaxis().set_ticks([]);
	plt.title('Phase Closure');
	plt.gca().set_xlabel("Range",fontsize=16);
	plt.gca().set_ylabel("Azimuth",fontsize=16);
	cb = plt.colorbar();
	cb.set_label('phase residual', size=16);
	plt.savefig(plotname);
	plt.close();
	return;

def make_histogram(histdata, plotname):
	plt.figure();
	plt.hist(histdata,bins=700);
	plt.yscale('log');
	plt.xlabel('Phase Difference (#*pi radians)');
	plt.ylabel('number of pixels');
	plt.savefig(plotname);
	plt.close();
	return;


if __name__=="__main__":
	loops_dir="Phase_Circuits/"
	loops_guide="loops.txt";
	all_loops=form_all_loops();
	show_images(all_loops,loops_dir,loops_guide);