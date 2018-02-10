# vim:set ff=unix expandtab ts=4 sw=4:
from functools import reduce
import numpy as np
from sympy import ceiling
from matplotlib.ticker import MaxNLocator
from .gv import indexed_color,indexed_filled_marker,filled_markers,indexcolors
from bgc_md.plot_helpers import add_xhist_data_to_scatter,xhist_fs,yhist_fs

from .DataFrame import DataFrame

def dict_plot(hist_dict,ax):
    x=np.arange(len(hist_dict))
    y=hist_dict.values()
   #print(x,y)
    ax.set_xticks(x)
    rects=ax.bar(x,y, color='g', alpha=0.75, align='center') 
    ax.set_xticklabels(hist_dict.keys(), rotation=90)

class ModelList(list):
    # the class should become the place where comparisons of Models are made
    # and get some methods to produce plots or report parts
    # this will eventually make it possible to get rid of plot_data in autogeneratedMd...
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
       #print(self)

    def plot_dependencies(self,target_key,ax):
       #print(target_key)
        #first find all keys
        all_keys=set()
        for model in self:
           #print(model.name)
            deps=model.find_keys_or_symbols_used_in_key(target_key)
           #print(deps)
            all_keys.update(deps)
        #now for every dependency find the number of models in which
        #target_key depends on it
        hist=dict()
        for dep in all_keys:
            hist[dep]=0
            for model in self:
                if dep in model.find_keys_or_symbols_used_in_key(target_key):
                    hist[dep]+=1
        dict_plot(hist,ax)   
        ax.set_ylabel("# models")
        
    def plot_model_key_dependencies_scatter_plot(self,target_key,ax):
       #print(target_key)
        #first find all keys
        all_keys=set()
        for model in self:
            #print(model.name)
            deps=model.find_keys_or_symbols_used_in_key(target_key)
            #print(deps)
            all_keys.update(deps)


        all_keys=list(all_keys)
        #now for every dependency find the number of models in which
        #target_key depends on it
        #x=np.arange(len(hist_dict))
        #y=np.arange(len(self))
        x_vals=range(len(all_keys))
        y_vals=range(len(self))
        model_names=[el.name for el in self]
        for y,mod in enumerate(self):
            keys=mod.find_keys_or_symbols_used_in_key(target_key)
            positions=[]
            for key in keys:
                positions.append(all_keys.index(key))
            ys=[y for p in positions]
            ax.scatter(positions,ys, s=100,alpha=0.9,  marker=indexed_filled_marker(y), c=indexed_color(y+20))
        ax.set_xticks(x_vals)
        ax.set_xticklabels(all_keys, rotation=90, fontsize=20)
        ax.set_xlabel("dependencies of " + target_key)
        ax.set_xlim((-1,max(x_vals)+1))
        
        ax.set_yticks(y_vals)
        ax.set_yticklabels(model_names, fontsize=20)
        ax.yaxis.set_label_coords(0, 1) 
        ax.set_ylabel("models", rotation=0)
        ax.set_ylim((-1,max(y_vals)+1))

        for tick in ax.xaxis.get_major_ticks():
            tick.label.set_fontsize(16) 
        for tick in ax.yaxis.get_major_ticks():
            tick.label.set_fontsize(16) 
       

    def  denpendency_plots_from_keys_in_compartments(self,fig):
        # Automatically produce denpendency plots from keys in compartments
        # 1st get all component keys
        target_keys_set=set()
        for m in self:
            for el in m.get_component_keys():
                if el !="state_vector_derivative":
                    target_keys_set.add(el)
        target_keys=list(target_keys_set)
        nr_hist = len(target_keys)
        fig.set_figheight(fig.get_figwidth()/8*nr_hist)
        # 2nd iterate over them 
        for target_key in target_keys:
        # 3rd check wich models actually provide the target_key
            sublist=ModelList([m for m in self if m.has_key(target_key)])
        # Plot! 
            count = target_keys.index(target_key)+1
            nr_columns=2
            nr_rows=ceiling(nr_hist/nr_columns)
            ax = fig.add_subplot(nr_rows,nr_columns, count) 
            sublist.plot_model_key_dependencies_scatter_plot(target_key,ax)
    
    def scatter_plus_hist_nr_vars_vs_nr_ops(self,ax):
        #collect data
        plot_data = DataFrame([['name', 'nr_ops','nr_vars']])
        for index, model in enumerate(self):
            ops = 0
            for i in range(model.rhs.rows):
                for j in range(model.rhs.cols):
                    ops += model.rhs[i,j].count_ops()

            data_list = [model.name, ops,len(model.variables)]
            plot_data.append_row(data_list)
        
        xdata = np.array(plot_data[:,'nr_vars'])
        ydata = np.array(plot_data[:,'nr_ops'])
        
        for i in range(plot_data.nrow):
#            ax.scatter(xdata[i]+(0.5-np.random.rand(1))*0.75,ydata[i], s=200, alpha=0.9, label=plot_data[i,'name'], c=indexed_color(i+20))
            ax.scatter(xdata[i],ydata[i], s=200, alpha=0.9, label=plot_data[i,'name'], marker=indexed_filled_marker(i), c=indexed_color(i+20))

        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width*0.4, box.height*0.6])
        #ax.legend(loc='center left', bbox_to_anchor=(1.05, 0.5), scatterpoints=1, frameon=False)
        ax.set_xlabel("# variables", fontsize = "22",  labelpad=20)
        ax.set_ylabel(r'# operations to calculate $\mathbf{f}_v(\mathbf{x}_v,t)$', fontsize = "22",  labelpad=20)
        add_xhist_data_to_scatter(ax, xdata, '# models', fontsize=xhist_fs)
    #    add_yhist_data_to_scatter(ax, ydata, '# models')
        