# vim:set ff=unix expandtab ts=4 sw=4:
from pathlib import Path
from functools import reduce
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sympy import sympify, solve, Symbol, limit, oo, ceiling, simplify, Matrix
from sympy.core import Atom
from matplotlib.ticker import MaxNLocator
from .gv import indexed_color,indexed_filled_marker,filled_markers,indexcolors
from bgc_md.plot_helpers import add_xhist_data_to_scatter,xhist_fs,yhist_fs
from bgc_md.ReportInfraStructure import ReportElementList, Header, Math, Meta, Text, Citation, Table, TableRow, Newline, MatplotlibFigure
from bgc_md.Model import Model, check_parameter_set_complete
from bgc_md.helpers import py2tex_silent, key_from_dict_by_value

from .DataFrame import DataFrame

def add_yhist_data_to_scatter(plot_ax, data, label, fontsize, show_grid = True):
    # add right y-axis with histogram data

    # add second y-axis at the right
    ax = plot_ax.twinx()
    ax.set_position(plot_ax.get_position())
    ax.set_ylim(plot_ax.get_ylim())

    # prepare data
    bins = [i for i in range(min(data),max(data)+2,1)]
    hisy = np.histogram(data,bins=bins)

    y2_ticks = [hisy[1][i] for i in range(len(hisy[0])) if hisy[0][i] != 0]
    y2_ticklabels = [hisy[0][i] for i in range (len(hisy[0])) if hisy[0][i] !=0]
    ax.set_yticks(y2_ticks)
    ax.set_yticklabels(y2_ticklabels, fontsize=fontsize)
    ax.set_ylabel(label, fontsize=fontsize)
    ax.grid(show_grid)


#fixme: probably working through side effects
def nice_hist(ax, data):
    bins = [i for i in range(min(data),max(data)+2,1)]
    his = np.histogram(data,bins=bins)
    ax.bar(his[1][:-1],his[0], width=1.0, align='center', color='g', alpha=0.75)
    ax.set_xticks(bins[:-1])
#    plt.xticks(bins[:-1], bins[:-1])
    ax.set_yticks(range(max(his[0])+1))
#    ax.hist(data, number_of_bins, normed=0, histtype='bar', facecolor='g', alpha=0.75)
    ax.set_xlim([bins[0]-0.5, bins[-1]-0.5])
    locator = MaxNLocator(nbins=10, integer=True)
    ax.xaxis.set_major_locator(locator)

def dict_plot(hist_dict,ax):
    x=np.arange(len(hist_dict))
    y=hist_dict.values()
   #print(x,y)
    ax.set_xticks(x)
    rects=ax.bar(x,y, color='g', alpha=0.75, align='center') 
    ax.set_xticklabels(hist_dict.keys(), rotation=90)

# needs a test
def exprs_to_element(exprs, symbols_by_type):
    if not exprs:
        return Text("-")

    # two possibilities in yaml file:
    # 1)    exprs: "C = ..."
    # 2)    exprs:
    #           - "C = ..."
    #           - "C = ..."
    # so this table entry will be treated as a list of expressions
    subl = ReportElementList([])
    if type(exprs) == type(""):
        expr_list = [exprs]
    elif type(exprs) == type([]):
        expr_list = exprs
    else:
        raise(Exception(str(exprs) + " is no valid list of expressions."))

    for index2, expr_string in enumerate(expr_list):
        if expr_string:
            # new line if not first entry
            if index2 > 0:
                subl.append(Newline()) 
            parts = expr_string.split("=",1)
            parts[0] = parts[0].strip()
            parts[1] = parts[1].strip()
            p1 = sympify(parts[0], locals=symbols_by_type)
            p2 = sympify(parts[1], locals=symbols_by_type)
            
            # this is a hybrid version that keeps 'f_s = I + A*C' in shape, but if 'Matrix(...)' comes into play, rearranging by sympify within the matrix cannot be prevented
            # comment it out for a a clean version regarding use of ReportElementList, but with showing 
            # 'f_s = A * C + I' instead
            try:
                p2 = py2tex_silent(parts[1])
            except TypeError:
               pass
            
            subl.append(Math("$p1=$p2", p1=p1,p2=p2))
    return subl


# fixme: what does this function really count?
def depth(expr):
    expr = sympify(expr)

    if isinstance(expr, Atom):
        return 1
    else:
        if len(expr.args) == 0:
            return 0
        return 1 + max([depth(arg) for arg in expr.args])

class ModelList(list):
    # the class should become the place where comparisons of Models are made
    # and get some methods to produce plots or report parts
    # this will eventually make it possible to get rid of plot_data in autogeneratedMd...
    @classmethod
    def from_dir_path(cls,input_path):
    
        if not input_path.exists():
            raise(Exception("The input path " + input_path.as_posix() + " does not exist."))
        
        model_list=cls(Model.from_path(p) for p in input_path.iterdir() if p.suffix == ".yaml")
        return(model_list)


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
        
    
    
    def create_overview_table(self, target_dir_path):
        # fixme mm:
        #   This method offensively misuses the class ReportElementList by 
        #   putting html code directly into the report elements 
        #   which defeats their purpose  of creating transformable output.
        #   It also writes files directly so it works throu side effects

        #   Either 
        #   1.) 
        #   we abandon the proposed multiformat approach by creating 
        #   html only and do not use the ReportElementList here or we  
        #
        #   2.)
        #   implement a table reportElement that is rich enough 
        #   to show what we want. In this case the html goes into the
        #   write_html method of the table and is replaced here by 
        #   the general format of the reportElement syntax.
        #
        # fixme mm:
        #  This method links to the Model reports and assumes that they live in
        #  directories named after the models and contain a Report.html
        #  this information is duplicated in the per Model report code.

        header = [Text(""), Text("Model"), Text("# Variables"), Text("# Parameters"), Text("# Constants"), Text("Component"), Text("Description"), Text("Expressions"), Text("fv/fs"), Text("Right hand side of ODE"), Text("Source")]
        table_format = list("lcccclcccl")
        rel2 = Text('''<script language="javascript">
        function ausklappen(id)
        {
            if (document.getElementById(id).style.display=="none")
            {
                document.getElementById(id).style.display="block";
            }
            else
            {
                document.getElementById(id).style.display="none";
            }
        }\n</script>\n''')
    
        rel2 += Text('<table>\n<thead><tr class="header">\n<th></th><th align="left">Model</th>\n<th align="center"># Variables</th>\n<th align="center"># Parameters</th>\n<th align="center"># Constants</th>\n<th align="center">Structure</th>\n<th align="center">Right hand side of ODE</th>\n<th align="left">Source</th>\n</tr>\n</thead>\n')
           
        header_row = TableRow(header)
        T = Table("Summary of the models in the database of Carbon Allocation in Vegetation models", header_row, table_format)
    
        compar_keys=["state_vector_derivative"]
        #plot_data = DataFrame([['name', 'nr_sv', 'nr_sym', 'nr_exprs', 'nr_ops', 'depth','nr_vars','nr_parms','part_scheme','s_scale','t_resol']+compar_keys])
        print('##################################################')
        for index, model in enumerate(self):
            print(type(model))
            print(model.name)
            # collect data for plots
            #data_list = [model.name]
    
            
            ops = 0
            d = 0
            for i in range(model.rhs.rows):
                for j in range(model.rhs.cols):
                    ops += model.rhs[i,j].count_ops()
                    d = max([d, depth(model.rhs[i,j])])
    
            
            if model.partitioning_scheme == "fixed": 
                boolean_part_scheme = 0
            else:
                boolean_part_scheme = 1
            state_vector_derivative_dep_set={"faked_key","another_faked_key"}
    
            #data_list += [nr_state_v, len(model.syms_dict), len(model.exprs_dict), ops, d,len(model.variables),len(model.parameters),boolean_part_scheme,model.space_scale,model.time_resolution,state_vector_derivative_dep_set]
            #plot_data.append_row(data_list)
            
            # create table
            dir_name = model.yaml_file_path.stem
            dir_path =target_dir_path.joinpath(dir_name)
            # the link is relative to target dir since this file is created there 
            report_link = str(dir_path.relative_to(target_dir_path).joinpath("Report.html"))
    
            l = [Text(model.name)]         
            rel2 += Text('<tbody>\n')
            parity = ['odd','even'][(index+1) % 2]
            rel2 += Text('<tr class="$p">\n', p=parity, i=index)
    
            image_string = ""
            reservoir_model = model.reservoir_model
            if reservoir_model:
                if not dir_path.exists():
                    dir_path.mkdir()
                image_file_name="Thumbnail.svg"
                image_file_path = dir_path.joinpath(image_file_name)
                fig = reservoir_model.figure(thumbnail=True)
                fig.savefig(image_file_path.as_posix(), transparent=True)
                plt.close(fig)
                # the link is relative to target dir since thi file is created there 
                image_string = '<img src="' + str(image_file_path.relative_to(target_dir_path)) + '"> '
    
            rel2 += Text('<td align="left">$image_string</td>', image_string=image_string)
            rel2 += Text('<td align="left"><a href="$rl" target="_blank">$mn</a></td>\n', rl=report_link, mn=model.name)
    
            l.append(Text(str(len(model.variables))))
            rel2 += Text('<td align="center" onclick="ausklappen(\'comp_table_$i\');ausklappen(\'rhs_$i\')">$n</td>\n', i=index, n=str(len(model.variables)))
    
            l += [Text(" ")]*5
            rel2 += Text('<td align="center" onclick="ausklappen(\'comp_table_$i\');ausklappen(\'rhs_$i\')">$n</td>\n', i=index, n=str(len(model.parameters)))
            rel2 += Text('<td align="center" onclick="ausklappen(\'comp_table_$i\');ausklappen(\'rhs_$i\')"></td>\n', i=index)
    
            fv_fs_entry = Text(" ")
            for row_dic in model.df.rows_as_dictionary:
                if row_dic['name'] in ('f_v', 'f_s'):
                    if 'exprs' in row_dic.keys() and row_dic['exprs']:
                        fv_fs_entry = exprs_to_element(row_dic['exprs'], model.symbols_by_type)
            l.append(fv_fs_entry)
    
            l.append(Math("$eq", eq=model.rhs))
            rest = Text('<td align="center" style="vertical-align:middle" onclick="ausklappen(\'comp_table_$i\');ausklappen(\'rhs_$i\')"><div id="rhs_$i" style="display:none">', i=index) + Math("$eq", eq=model.rhs) + Text("</div></td>\n")
            l.append(Citation(model.bibtex_entry, parentheses=False))
            rest += Text('<td align="left" onclick="ausklappen(\'comp_table_$i\');ausklappen(\'rhs_$i\')">', i=index) + Citation(model.bibtex_entry, parentheses=False) + Text("</td>\n</tr>\n")
            row = TableRow(l)
            T.add_row(row)
    
            rel2 += Text('<td align="center" onclick="ausklappen(\'comp_table_$i\');ausklappen(\'rhs_$i\')">', i=index) + fv_fs_entry
            rel2 += Text('\n<div id="comp_table_$i" style="display:none">\n',i=index)
            comp_t = Text('<table>\n<tr class="header">\n<th align="center">Component</th>\n<th align="left">Description</th>\n<th align="center">Expressions</th>\n</tr>\n</thead>\n')
            comp_t += Text("<tbody>\n")
            is_comp = False
            for row_dic in model.df.rows_as_dictionary:
                if row_dic['category'] in ('components') and row_dic['name'] not in ('fv', 'fs'):
                    is_comp = True
                    l = [Newline()]*4
    
                    l.append(Math("$sv", sv=sympify(row_dic['name'], locals=model.symbols_by_type)))
                    comp_t += Text('<tr>\n<td align="center">') +Math("$sv", sv=sympify(row_dic['name'], locals=model.symbols_by_type)) + Text("</td>\n")
    
                    if row_dic['desc']:
                        l.append(Text("$d" , d=row_dic['desc']))
                        comp_t += Text('<td align="left">$d</td>\n',d=row_dic['desc'])
                    else:
                        l.append(Text("-"))
                        comp_t += Text('<td align="left">-</td>\n')
    
                    if row_dic['exprs']:
                        l.append(exprs_to_element(row_dic['exprs'], model.symbols_by_type))
                        comp_t += Text('<td align="center">') + exprs_to_element(row_dic['exprs'], model.symbols_by_type) + Text("</td>\n")
                    else:
                        l.append(Text("-"))
                        comp_t += Text('<td align="center">-</td>\n')
    
                    l += [Newline()]*3
    
                    row = TableRow(l)
                    T.add_row(row)                    
                    comp_t += Text("</tr>\n")
    
            comp_t += Text("</tbody>\n</table>\n</td>\n")
            if is_comp:
                rel2 += comp_t
            rel2 += Text("</div>\n")
            rel2 += rest
    
        #rel += T
        rel2 += Text("</tbody>\n</table>\n")
        return rel2
    
    def create_scatter_plot_symbols_operations(self):
        rel=ReportElementList()
        fig = plt.figure(figsize=(15,10))
    
        ax = fig.add_subplot(1,1,1)
        self.scatter_plus_hist_nr_vars_vs_nr_ops(ax)
        #if model_type == 'soil_model':
        #    ax.set_ylabel(' operations to calculate $\mathbf{f}_s(\mathbf{C},t)$', fontsize = 22)
        ax.set_ylabel(' operations to calculate Right hand side of ODE', fontsize = 22)
        rel += MatplotlibFigure(fig,"Figure 4b", "# variables & # operations")
        return rel
    

    def create_scatter_plot_symbols_depth_of_operations(self):
        
        fig = plt.figure(figsize=(10,10)) # figure size including legend
    
        ax = fig.add_subplot(1,1,1)
        xdata = np.array(plot_data[:,'nr_vars'])
        ydata = np.array(plot_data[:,'depth'])
    
        for i in range(plot_data.nrow):
            ax.scatter(xdata[i],ydata[i], s=200, alpha=0.9, label=plot_data[i,'name'], marker=filled_markers[i], c=indexcolors[i+20])
    
        box = ax.get_position()
        ax.set_position([box.x0, box.y0+box.height*0.4, box.width, box.height*0.6])
        ax.legend(loc='lower center', bbox_to_anchor=(0.5, -box.height*0.8), scatterpoints=1, frameon = False, ncol = 2)
    #    ax.legend(loc='lower center', scatterpoints=1, frameon = False, ncol = 2)
        ax.set_xlabel("# variables", fontsize = "22",  labelpad=20)
        if model_type == 'vegetation_model':
            ax.set_ylabel('cascading depth of operations\n' + r'to calculate $\mathbf{f}_v(\mathbf{x}_v,t)$', fontsize = 22)
        if model_type == 'soil_model':
            ax.set_ylabel('cascading depth of operations\n' + r'to calculate $\mathbf{f}_s(\mathbf{C},t)$', fontsize = 22)
    
        ax.set_ylim((0,max(ydata)+1))
    
        # change font size for the tick labels
        for tick in ax.xaxis.get_major_ticks():
            tick.label.set_fontsize(20) 
        for tick in ax.yaxis.get_major_ticks():
            tick.label.set_fontsize(20) 
    
        add_xhist_data_to_scatter(ax, xdata, ' models', fontsize=xhist_fs)
        add_yhist_data_to_scatter(ax, ydata, ' models', fontsize=yhist_fs)
        plt.rcdefaults()
        rel += MatplotlibFigure(fig,"Figure 5", "# variables & cascading depth of operations")
        return rel

    def create_scatter_plot_variables_parameters(self):
        rel=ReportElementList()
        plot_data = DataFrame([['name','nr_vars','nr_parms']])
        for index, model in enumerate(self):
            data_list = [model.name,len(model.variables),len(model.parameters)]
            plot_data.append_row(data_list)
        
        xhist_fs = 16
        yhist_fs = 16
    
        # variables vs. parameters
        fig = plt.figure(figsize=(10,10))
    
        ax = fig.add_subplot(1,1,1)
        xdata = np.array(plot_data[:,'nr_vars'])
        ydata = np.array(plot_data[:,'nr_parms'])
    
        for i in range(plot_data.nrow):
            #ax.scatter(xdata[i],ydata[i], s=200, alpha=0.9, label=plot_data[i,'name'], c=indexcolors[i+20])
            ax.scatter(xdata[i],ydata[i], s=200, alpha=0.9, label=plot_data[i,'name'], marker=filled_markers[i], c=indexcolors[i+20])
    
        box = ax.get_position()
        ax.set_position([box.x0, box.y0+box.height*0.4, box.width, box.height*0.6])
        ax.legend(loc='lower center', bbox_to_anchor=(0.5, -box.height*0.8), scatterpoints=1, frameon = False, ncol = 2)
        ax.set_xlabel("# variables", fontsize = "22",  labelpad=20)
        ax.set_ylabel("# parameters", fontsize = "22",  labelpad=20)
        ax.set_ylim((0,max(ydata)+1))
    
        # change font size for the tick labels
        for tick in ax.xaxis.get_major_ticks():
            tick.label.set_fontsize(20) 
        for tick in ax.yaxis.get_major_ticks():
            tick.label.set_fontsize(20) 
    
        add_xhist_data_to_scatter(ax, xdata, ' models', fontsize=xhist_fs)
        add_yhist_data_to_scatter(ax, ydata, ' models', fontsize=yhist_fs)
    
        rel += MatplotlibFigure(fig,"Figure 4", "# variables & parameters")
        return rel
    
    def create_state_variable_parameter_variable_histograms(self):
        rel=ReportElementList()
        # first line of histograms
        nr_hist = 3
        fig1 = plt.figure(figsize=(15,5), tight_layout=True)
        plot_data = DataFrame([['name', 'nr_sv', 'nr_vars','nr_parms']])
        for index, model in enumerate(self):
            data_list = [model.name,model.nr_state_v,len(model.variables),len(model.parameters)]
            plot_data.append_row(data_list)
        # state variables and models
        ax = fig1.add_subplot(1, nr_hist, 1)
        data = np.array(plot_data[:,'nr_sv'])
        nice_hist(ax, data)
        ax.set_xlabel("# state variables", fontsize = "22",  labelpad=20)
        ax.set_ylabel("# models", fontsize = "22",  labelpad=20)
        # change font size for the tick labels
        for tick in ax.xaxis.get_major_ticks():
            tick.label.set_fontsize(20) 
        for tick in ax.yaxis.get_major_ticks():
            tick.label.set_fontsize(20) 
    
        # parameters and models
        ax = fig1.add_subplot(1, nr_hist, 2)
        data = np.array(plot_data[:,'nr_parms'])
        nice_hist(ax, data)
        ax.set_xlabel("# parameters", fontsize = "22",  labelpad=20)
        ax.set_ylabel("# models", fontsize = "22",  labelpad=20)
         
        for tick in ax.xaxis.get_major_ticks():
            tick.label.set_fontsize(20) 
        for tick in ax.yaxis.get_major_ticks():
            tick.label.set_fontsize(20) 
    
        # variables and models
        ax = fig1.add_subplot(1, nr_hist, 3)
        data = np.array(plot_data[:,'nr_vars'])
        nice_hist(ax, data)
        ax.set_xlabel("# variables", fontsize = "22",  labelpad=20)
        ax.set_ylabel("# models", fontsize = "22",  labelpad=20)
    
        for tick in ax.xaxis.get_major_ticks():
            tick.label.set_fontsize(20) 
        for tick in ax.yaxis.get_major_ticks():
            tick.label.set_fontsize(20) 
    
        # variables and models
        #rel += Text(mpld3.fig_to_html(fig1))
        rel += MatplotlibFigure(fig1,"Figure 1","Histograms, # variables") 
    
        # # second line 
        # target_key="state_vector_derivative"
        # sublist=ModelList([m for m in model_list if m.has_key(target_key)])
        # nr_hist = 2
        # fig1 = plt.figure(figsize=(30,15), tight_layout=True)
        # ax = fig1.add_subplot(nr_hist,1,1)
        # # first check wich models actually provide the target_key we are looking for
        # sublist.plot_dependencies(target_key,ax)
        # ax = fig1.add_subplot(nr_hist,1,2)
        # sublist.plot_model_key_dependencies_scatter_plot(target_key,ax)
        #
        # rel += MatplotlibFigure(fig1,"Figure 2","Dependencies of the right hand side of the ODEs") 
        #
        # fig1 = plt.figure(figsize=(30,1), tight_layout=True) 
        # plt.rcdefaults()
        # # note that the second argument 1 in figsize is required by matplotlib 
        # # but ignored by the following method because the 
        # # height will be adapted inside the method
        #
        # ModelList(model_list).denpendency_plots_from_keys_in_compartments(fig1)
        # rel += MatplotlibFigure(fig1,"Figure 3","dependency plots of compartment variables") 
        return rel
    #
        
    def create_overview_report(self, target_dir_path=Path('.'),output_file_name='list_report.html'):
        output_path = target_dir_path.joinpath(output_file_name)
        if not target_dir_path.exists():
            target_dir_path.mkdir()
    
        rel = Header('Overview of the models', 1)
    
        #fixme mm:
        # the fact thet the following mehtod has a target_dir_path argument
        # points to it having side effects
        rel += self.create_overview_table(target_dir_path)
    
        ## create the plots
    
        rel += Header("Figures", 1)
        rel += self.create_state_variable_parameter_variable_histograms()
    
        #plot_data = DataFrame([['name', 'nr_sv', 'nr_sym', 'nr_exprs', 'nr_ops', 'depth','nr_vars','nr_parms','part_scheme','s_scale','t_resol']+compar_keys])
    
            #data_list += [nr_state_v, len(model.syms_dict), len(model.exprs_dict), ops, d,len(model.variables),len(model.parameters),boolean_part_scheme,model.space_scale,model.time_resolution,state_vector_derivative_dep_set]

        # scatter plots
        rel +=self.create_scatter_plot_variables_parameters()
    
        ## symbols and operations
        rel +=self.create_scatter_plot_symbols_operations()
    
        ## symbols and depth of operations
        rel +=self.create_scatter_plot_symbols_depth_of_operations()
    
       
        ## number of operations and depth of operations
        #fig = plt.figure(figsize=(10,10))
    
        #ax = fig.add_subplot(1,1,1)
        #xdata = np.array(plot_data[:,'nr_ops'])
        #ydata = np.array(plot_data[:,'depth'])
    
    
        #for i in range(plot_data.nrow):
        #    #ax.scatter(xdata[i]+(0.5-np.random.rand(1))*0.75,ydata[i], s=200, alpha=0.9, label=plot_data[i,'name'], c=indexcolors[i+20])
        #    ax.scatter(xdata[i],ydata[i], s=200, alpha=0.9, label=plot_data[i,'name'], marker=filled_markers[i], c=indexcolors[i+20])
    
        #box = ax.get_position()
        #ax.set_position([box.x0, box.y0+box.height*0.4, box.width, box.height*0.6])
        #ax.legend(loc='lower center', bbox_to_anchor=(0.5, -box.height*0.8), scatterpoints=1, frameon = False, ncol = 2)
        #if model_type == 'vegetation_model':
        #    ax.set_xlabel(r' operations to calculate $\mathbf{f}_v(\mathbf{x}_v,t)$', fontsize = "22",  labelpad=20)
        #    ax.set_ylabel('cascading depth of operations\n' + r'to calculate $\mathbf{f}_v(\mathbf{x}_v,t)$', fontsize = "22",  labelpad=20)
        #if model_type == 'soil_model':
        #    ax.set_xlabel(r' operations to calculate $\mathbf{f}_s(\mathbf{C},t)$', fontsize = "22",  labelpad=20)
        #    ax.set_ylabel('cascading depth of operations\n' + r'to calculate $\mathbf{f}_s(\mathbf{C},t)$', fontsize = "22",  labelpad=20)
        #ax.yaxis.labelpad = 0
    
        ## change font size for the tick labels
        #for tick in ax.xaxis.get_major_ticks():
        #    tick.label.set_fontsize(20) 
        #for tick in ax.yaxis.get_major_ticks():
        #    tick.label.set_fontsize(20) 
        #ax.set_ylim((0,max(ydata)+1))
        #ax.set_xlim((0,max(xdata)+50))
    
    #   # add_xhist_data_to_scatter(ax, xdata, ' models')
        #add_yhist_data_to_scatter(ax, ydata, ' models', fontsize=yhist_fs)
        #rel += MatplotlibFigure(fig,"Figure 6", "cascading depth and # operations")
    
        ## partitioning scheme and number of operations
        #if model_type == 'vegetation_model':
        #    fig = plt.figure(figsize=(8,5))
        #    fig.subplots_adjust(bottom=0.2, top=0.8, left=0.2)
        #
        #    ax = fig.add_subplot(1,1,1)
        #    xdata = np.array(plot_data[:,'part_scheme'])
        #    ydata = np.array(plot_data[:,'nr_ops'])
        #
        #    for i in range(plot_data.nrow):
        #        #ax.scatter(xdata[i]+(0.5-np.random.rand(1))*0.1,ydata[i], s=200, alpha=0.9, label=plot_data[i,'name'], c=indexcolors[i+20])
        #        ax.scatter(xdata[i],ydata[i], s=200, alpha=0.9, label=plot_data[i,'name'], marker=filled_markers[i], c=indexcolors[i+20])
        #
        #    box = ax.get_position()
        #    ax.set_position([box.x0, box.y0, box.width * 0.4, box.height])
        #    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), scatterpoints=1, frameon=False)
        #    ax.set_xlabel("partitioning scheme", fontsize = "22", labelpad=25)
        #    ax.set_ylabel(' operations to\n' + r'calculate $\mathbf{f}_v(\mathbf{x}_v,t)$', fontsize = "22", labelpad=25)
        ##    ax.yaxis.label.set_position([-0.2,0])
        #    ax.set_ylim((0,max(ydata)+10))
        #    ax.set_xlim((-0.2,max(xdata)+0.2))
        #    ax.set_xticks([0,1])
        #    ax.set_xticklabels(['fixed','dynamic'])
        #
        #    for tick in ax.xaxis.get_major_ticks():
        #        tick.label.set_fontsize(16) 
        #    for tick in ax.yaxis.get_major_ticks():
        #        tick.label.set_fontsize(16) 
        #
        #    add_xhist_data_to_scatter(ax, xdata, ' models', fontsize=16)
        #
        #    rel += MatplotlibFigure(fig,"Figure 7", "Type of carbon partitioning scheme among pools and # operations")
    
        rel += Header("Bibliography", 1)
        rel.write_pandoc_html(output_path.as_posix())

