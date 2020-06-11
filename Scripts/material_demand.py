# Material Demands for the US Building Stock
#
# Calculate the future building stock-wide material demand for buildings
#   based upon the material intensity of buidings today. Validate this bottom-up approach
#   with top-down economic data.

# import libraries
import pandas as pd
import matplotlib.pyplot as plt
from odym import dynamic_stock_model as dsm
import numpy as np

# ----------------------------------------------------------------------------------------------------
# load in data from other scripts and excels
structure_data_historical = pd.read_csv('./InputData/HAZUS_weight.csv')

FA_dsm_SSP1 = pd.read_excel('./Results/SSP_dsm.xlsx', sheet_name='SSP1')
FA_dsm_SSP1 = FA_dsm_SSP1.set_index('time',drop=False)
# FA_dsm_SSP2 = pd.read_excel('./Results/SSP_dsm.xlsx', sheet_name='SSP2')
# FA_dsm_SSP2 = FA_dsm_SSP1.set_index('time',drop=False)
# FA_dsm_SSP3 = pd.read_excel('./Results/SSP_dsm.xlsx', sheet_name='SSP3')
# FA_dsm_SSP3 = FA_dsm_SSP1.set_index('time',drop=False)
# FA_dsm_SSP4 = pd.read_excel('./Results/SSP_dsm.xlsx', sheet_name='SSP4')
# FA_dsm_SSP4 = FA_dsm_SSP1.set_index('time',drop=False)
# FA_dsm_SSP5 = pd.read_excel('./Results/SSP_dsm.xlsx', sheet_name='SSP5')
# FA_dsm_SSP5 = FA_dsm_SSP1.set_index('time',drop=False)

FA_sc_SSP1 = pd.read_excel('./Results/SSP_dsm.xlsx', sheet_name='SSP1_sc')
# FA_sc_SSP2 = pd.read_excel('./Results/SSP_dsm.xlsx', sheet_name='SSP2_sc')
# FA_sc_SSP3 = pd.read_excel('./Results/SSP_dsm.xlsx', sheet_name='SSP3_sc')
# FA_sc_SSP4 = pd.read_excel('./Results/SSP_dsm.xlsx', sheet_name='SSP4_sc')
# FA_sc_SSP5 = pd.read_excel('./Results/SSP_dsm.xlsx', sheet_name='SSP5_sc')

materials_intensity = pd.read_excel('./InputData/Material_data.xlsx', sheet_name='SSP1_density')
materials_intensity_df = materials_intensity.set_index('Structure_Type', drop=True)
materials_intensity_df = materials_intensity_df.transpose()
materials_intensity_df = materials_intensity_df.drop(index='Source')

scenario_df = pd.read_excel('./InputData/Material_data.xlsx', sheet_name='Scenarios')
scenario_df = scenario_df.set_index('Scenario')

## ----------------------------------------------------------------------------------------------------
# set years series
years_future = FA_dsm_SSP1['time'].iloc[197:]
years_all = FA_dsm_SSP1.index.to_series()

# compute a lifetime distribution
def generate_lt(type, par1, par2):
    ''' Normal: par1  = mean, par2 = std. dev
        Weibull: par1 = shape, par2 = scale'''

    # ---- Building lifespan distributions ----
    # BldgLife_mean_res = 80  # years
    # BldgLife_StdDev_res = 0.2 *  np.array([BldgLife_mean_res] * len(years))
    # BldgLife_mean_com = 70  # years
    # BldgLife_StdDev_com = 0.2 *  np.array([BldgLife_mean_com] * len(years))
    # BldgLife_mean_pub = 90  # years
    # BldgLife_StdDev_pub = 0.2 * np.array([BldgLife_mean_com] * len(years))
    if type=='Normal':
        # Normal
        lt = {'Type': type, 'Mean': np.array([par1] * len(years_all)), 'StdDev': np.array([par2])}
    elif type=='Weibull':
        # Weibull
        # lt_res = {'Type': 'Weibull', 'Shape': np.array([4.16343417]), 'Scale': np.array([85.18683893])}     # deetman_2018_res_distr_weibull
        # lt_res = {'Type': 'Weibull', 'Shape': np.array([5.5]), 'Scale': np.array([85.8])}
        # lt_com = {'Type': 'Weibull', 'Shape': np.array([4.8]), 'Scale': np.array([75.1])}
        # lt_res = {'Type': type, 'Shape': np.array([5]), 'Scale': np.array([130])}
        # lt_com = {'Type': type, 'Shape': np.array([3]), 'Scale': np.array([100])}
        # lt_pub = {'Type': type, 'Shape': np.array([6.1]), 'Scale': np.array([95.6])}
        lt = {'Type': type, 'Shape': np.array([par1]), 'Scale': np.array([par2])}
    return lt

# Debugging
# lt_existing = generate_lt('Weibull',par1=5, par2=100)        # lifetime distribution for existing buildings (all)
# lt_future = generate_lt('Weibull', par1=5, par2=100)

# Lifetime parameters
lt_existing = generate_lt('Weibull',par1=((0.773497 * 5) + (0.142467 * 4.8) + (0.030018 * 6.1)), par2=((0.773497 * 100) + (0.142467 * 75.1) + (0.030018 * 95.6)))        # weighted average of res, com, and pub
lt_future = generate_lt('Weibull',par1=((0.773497 * 5) + (0.142467 * 4.8) + (0.030018 * 6.1)), par2=((0.773497 * 100) + (0.142467 * 75.1) + (0.030018 * 95.6)))        # weighted average of res, com, and pub

# of outflow of each structural system type for already built buildings (before 2017). No new construction is considered in this analysis
def determine_outflow_existing_bldgs(FA_sc_SSP, plot=True, plot_title=''):
    '''Input a floor area stock-cohort matrix for each SSP and compute the outflow for each structural system that are already built.
     Key assumption is that construction techniques are the same each year. '''

    # compute an outflow for the existing stock using a "compute evolution from initial stock method"
    def determine_outflow_by_ss(lt=lt_existing, FA_sc_df=FA_sc_SSP, switch_year=196, frac_stock=1.0):
        '''Compute the outflow of the existing building stock with no additional inflow.
        A switch year of 196 represents 2016.
        frac_stock is the ratio of the exisitng building stock that is a particular structural system.
        For frac_stock = 1.0, all of the stock is considered to be the same. '''
        DSM_existing_stock = dsm.DynamicStockModel(t=years_all, lt=lt_existing)
        S_C = DSM_existing_stock.compute_evolution_initialstock(InitialStock=FA_sc_SSP.loc[(switch_year - 1), 0:(switch_year - 1)] * frac_stock, SwitchTime=switch_year)

        # compute outflow
        O_C = DSM_existing_stock.o_c[1::, :] = -1 * np.diff(DSM_existing_stock.s_c, n=1, axis=0)
        O_C = DSM_existing_stock.o_c[np.diag_indices(len(DSM_existing_stock.t))] = 0 - np.diag(
            DSM_existing_stock.s_c)  # allow for outflow in year 0 already
        O = DSM_existing_stock.compute_outflow_total()
        # compute stock
        S = DSM_existing_stock.s_c.sum(axis=1)
        outflow_df = pd.DataFrame({'time': DSM_existing_stock.t, 'outflow': O, 'stock': S})
        return outflow_df

    existing_outflow_total = determine_outflow_by_ss(lt=lt_existing,FA_sc_df=FA_sc_SSP,switch_year=196, frac_stock=1.0)
    existing_outflow_LF_wood = determine_outflow_by_ss(lt=lt_existing,FA_sc_df=FA_sc_SSP,switch_year=196, frac_stock=structure_data_historical.LF_wood[0])
    existing_outflow_Mass_Timber = determine_outflow_by_ss(lt=lt_existing,FA_sc_df=FA_sc_SSP,switch_year=196, frac_stock=structure_data_historical.Mass_Timber[0])
    existing_outflow_Steel = determine_outflow_by_ss(lt=lt_existing,FA_sc_df=FA_sc_SSP,switch_year=196, frac_stock=structure_data_historical.Steel[0])
    existing_outflow_RC = determine_outflow_by_ss(lt=lt_existing,FA_sc_df=FA_sc_SSP,switch_year=196, frac_stock=structure_data_historical.RC[0])
    existing_outflow_RM = determine_outflow_by_ss(lt=lt_existing,FA_sc_df=FA_sc_SSP,switch_year=196, frac_stock=structure_data_historical.RM[0])
    existing_outflow_URM = determine_outflow_by_ss(lt=lt_existing,FA_sc_df=FA_sc_SSP,switch_year=196, frac_stock=structure_data_historical.URM[0])
    existing_outflow_MH = determine_outflow_by_ss(lt=lt_existing,FA_sc_df=FA_sc_SSP,switch_year=196, frac_stock=structure_data_historical.MH[0])

    existing_outflow_all = pd.DataFrame({
                                         'outflow_LF_wood': existing_outflow_LF_wood.outflow,
                                         'stock_LF_wood': existing_outflow_LF_wood.stock,
                                         'outflow_Mass_Timber': existing_outflow_Mass_Timber.outflow,
                                         'stock_Mass_Timber': existing_outflow_Mass_Timber.stock,
                                         'outflow_Steel': existing_outflow_Steel.outflow,
                                         'stock_Steel': existing_outflow_Steel.stock,
                                         'outflow_RC': existing_outflow_RC.outflow,
                                         'stock_RC': existing_outflow_RC.stock,
                                         'outflow_RM': existing_outflow_RM.outflow,
                                         'stock_RM': existing_outflow_RM.stock,
                                         'outflow_URM': existing_outflow_URM.outflow,
                                         'stock_URM': existing_outflow_URM.stock,
                                         'outflow_MH': existing_outflow_MH.outflow,
                                         'stock_MH': existing_outflow_MH.stock,
                                         'total_outflow': existing_outflow_total.outflow,
                                         'total_stock': existing_outflow_total.stock
                                        })
    existing_outflow_all = existing_outflow_all.set_index(FA_dsm_SSP1['time'])
    if plot == True:
        # plot the outflow and the stock
        existing_outflow = existing_outflow_all.loc[:, existing_outflow_all.columns.str.contains('outflow')]
        existing_stock = existing_outflow_all.loc[:, existing_outflow_all.columns.str.contains('stock')]

        existing_outflow.iloc[197:].plot.line()
        plt.ylabel('Floor Area (Mm2)')
        plt.title(plot_title + ': Outflow of Buildings Constructed before 2017')
        plt.show();

        existing_stock.iloc[197:].plot.line()
        plt.ylabel('Floor Area (Mm2)')
        plt.title(plot_title + ': Stock of Buildings Constructed before 2017')
        plt.show();


        # existing_outflow_all.iloc[197:].plot.line()
        # plt.ylabel('Floor Area (Mm2)')
        # plt.title(plot_title + ': Outflow of Buildings Constructed before 2017')
        # plt.show()
    return existing_outflow_all

# area by structural system of outlow and stock of all existing buildings (built before 2017)
os_existing_SSP1 = determine_outflow_existing_bldgs(FA_sc_SSP=FA_sc_SSP1, plot=True, plot_title='SSP1')
# os_existing_SSP2 = determine_outflow_existing_bldgs(FA_sc_SSP=FA_sc_SSP2, plot=True, plot_title='SSP2')
# os_existing_SSP3 = determine_outflow_existing_bldgs(FA_sc_SSP=FA_sc_SSP3, plot=True, plot_title='SSP3')
# os_existing_SSP4 = determine_outflow_existing_bldgs(FA_sc_SSP=FA_sc_SSP4, plot=True, plot_title='SSP4')
# os_existing_SSP5 = determine_outflow_existing_bldgs(FA_sc_SSP=FA_sc_SSP5, plot=True, plot_title='SSP5')


def determine_inflow_outflow_new_bldg(scenario, FA_dsm_SSP=FA_dsm_SSP1, lt=lt_future, plot=True, plot_title='SSP1 '):
    # Select a scenario
    # scenario = 'S_0'    # new construction is same as exiting building stock
    # scenario = 'S_timber_high'      # High timber adoption

    # clean df
    FA_dsm_SSP = FA_dsm_SSP.set_index('time')
    structure_data_scenario = pd.DataFrame(
        {'LF_wood': scenario_df.LF_wood[scenario],
        'Mass_Timber': scenario_df.Mass_Timber[scenario],
        'Steel': scenario_df.Steel[scenario],
        'RC': scenario_df.RC[scenario],
        'RM': scenario_df.RM[scenario],
        'URM': scenario_df.URM[scenario],
        'MH': scenario_df.MH[scenario]},
    index=[0])

    # separate inflow by structural system ratio for each scenario
    inflow_SSP_all = pd.DataFrame(
        {'inflow_total' : FA_dsm_SSP.loc[2017:2100, 'inflow_total'],
         'inflow_LF_wood' : FA_dsm_SSP.loc[2017:2100, 'inflow_total'] * structure_data_scenario.LF_wood[0],
         'inflow_Mass_Timber': FA_dsm_SSP.loc[2017:2100, 'inflow_total'] * structure_data_scenario.Mass_Timber[0],
         'inflow_Steel': FA_dsm_SSP.loc[2017:2100, 'inflow_total'] * structure_data_scenario.Steel[0],
         'inflow_RC': FA_dsm_SSP.loc[2017:2100, 'inflow_total'] * structure_data_scenario.RC[0],
         'inflow_RM': FA_dsm_SSP.loc[2017:2100, 'inflow_total'] * structure_data_scenario.RM[0],
         'inflow_URM': FA_dsm_SSP.loc[2017:2100, 'inflow_total'] * structure_data_scenario.URM[0],
         'inflow_MH': FA_dsm_SSP.loc[2017:2100, 'inflow_total'] * structure_data_scenario.MH[0],
        }
    )

    def compute_inflow_driven_model_ea_ss(structural_system):
        ''' Compute an inflow driven model for each structural system.
         The lifetime distribution in the future is assumed to be the input lt for each scenario'''
        # compute a inflow driven model for each structural system
        DSM_Inflow_x = dsm.DynamicStockModel(t=years_future, i=inflow_SSP_all['inflow_' + structural_system], lt=lt)
        # CheckStr = DSM_Inflow.dimension_check()
        # print(CheckStr)

        S_C = DSM_Inflow_x.compute_s_c_inflow_driven()
        O_C = DSM_Inflow_x.compute_o_c_from_s_c()
        S = DSM_Inflow_x.compute_stock_total()
        O = DSM_Inflow_x.compute_outflow_total()
        DSM_Inflow_x.o = pd.Series(DSM_Inflow_x.o, index=DSM_Inflow_x.t)
        return DSM_Inflow_x

    # compute an inflow driven model for new construction in the future
    DSM_Inflow_LF_wood = compute_inflow_driven_model_ea_ss(structural_system='LF_wood')
    DSM_Inflow_Mass_Timber = compute_inflow_driven_model_ea_ss('Mass_Timber')
    DSM_Inflow_Steel = compute_inflow_driven_model_ea_ss('Steel')
    DSM_Inflow_RC = compute_inflow_driven_model_ea_ss('RC')
    DSM_Inflow_RM = compute_inflow_driven_model_ea_ss('RM')
    DSM_Inflow_URM = compute_inflow_driven_model_ea_ss('URM')
    DSM_Inflow_MH = compute_inflow_driven_model_ea_ss('MH')

    # summary dataframe of all DSM stocks, inflows, outflows
    DSM_Future_all = pd.DataFrame({
        'inflow_LF_wood' : DSM_Inflow_LF_wood.i,
        'outflow_LF_wood': DSM_Inflow_LF_wood.o,
        'stock_LF_wood': DSM_Inflow_LF_wood.s,
        'inflow_Mass_Timber': DSM_Inflow_Mass_Timber.i,
        'outflow_Mass_Timber': DSM_Inflow_Mass_Timber.o,
        'stock_Mass_Timber': DSM_Inflow_Mass_Timber.s,
        'inflow_Steel': DSM_Inflow_Steel.i,
        'outflow_Steel': DSM_Inflow_Steel.o,
        'stock_Steel': DSM_Inflow_Steel.s,
        'inflow_RC': DSM_Inflow_RC.i,
        'outflow_RC': DSM_Inflow_RC.o,
        'stock_RC': DSM_Inflow_RC.s,
        'inflow_RM': DSM_Inflow_RM.i,
        'outflow_RM': DSM_Inflow_RM.o,
        'stock_RM': DSM_Inflow_RM.s,
        'inflow_URM': DSM_Inflow_URM.i,
        'outflow_URM': DSM_Inflow_URM.o,
        'stock_URM': DSM_Inflow_URM.s,
        'inflow_MH': DSM_Inflow_MH.i,
        'outflow_MH': DSM_Inflow_MH.o,
        'stock_MH': DSM_Inflow_MH.s,
        'total_inflow':  DSM_Inflow_LF_wood.i + DSM_Inflow_Mass_Timber.i + DSM_Inflow_Steel.i + DSM_Inflow_RC.i + DSM_Inflow_RM.i + DSM_Inflow_URM.i + DSM_Inflow_MH.i,
        'total_outflow': DSM_Inflow_LF_wood.o + DSM_Inflow_Mass_Timber.o + DSM_Inflow_Steel.o + DSM_Inflow_RC.o + DSM_Inflow_RM.o + DSM_Inflow_URM.o + DSM_Inflow_MH.o,
        'total_stock':   DSM_Inflow_LF_wood.s + DSM_Inflow_Mass_Timber.s + DSM_Inflow_Steel.s + DSM_Inflow_RC.s + DSM_Inflow_RM.s + DSM_Inflow_URM.s + DSM_Inflow_MH.s
    })

    if plot==True:
        DSM_Future_Inflow = DSM_Future_all.loc[:, DSM_Future_all.columns.str.contains('inflow')]
        DSM_Future_Outflow = DSM_Future_all.loc[:, DSM_Future_all.columns.str.contains('outflow')]
        DSM_Future_Stock = DSM_Future_all.loc[:, DSM_Future_all.columns.str.contains('stock')]

        DSM_Future_Inflow.plot.line()
        plt.ylabel('Floor Area (Mm2)')
        plt.title(plot_title + ' ' + scenario + ' ' + 'Floor Area Inflow (New Construction) by Structural System')
        plt.show();

        DSM_Future_Outflow.plot.line()
        plt.ylabel('Floor Area (Mm2)')
        plt.title(plot_title + ' ' + scenario + ' ' + 'Floor Area Outflow (New Construction) by Structural System')
        plt.show();

        DSM_Future_Stock.plot.line()
        plt.ylabel('Floor Area (Mm2)')
        plt.title(plot_title + ' ' + scenario + ' ' + 'Floor Area Stock (New Construction) by Structural System')
        plt.show();

    return DSM_Future_all

# area by structural system of stock, inflow, and outflow of all new buildings (built after 2017)
sio_new_bldg_SSP1 = determine_inflow_outflow_new_bldg(scenario='S_0',FA_dsm_SSP=FA_dsm_SSP1, lt=lt_future, plot=True, plot_title='SSP1 ')
# sio_new_bldg_SSP2 = determine_inflow_outflow_new_bldg('S_timber_high',FA_dsm_SSP=FA_dsm_SSP2, lt=lt_future, plot=False, plot_title='SSP2 ')
# sio_new_bldg_SSP3 = determine_inflow_outflow_new_bldg('S_timber_high',FA_dsm_SSP=FA_dsm_SSP3,lt=lt_future,  plot=False, plot_title='SSP3 ')
# sio_new_bldg_SSP4 = determine_inflow_outflow_new_bldg('S_timber_high',FA_dsm_SSP=FA_dsm_SSP4, lt=lt_future, plot=False, plot_title='SSP4 ')
# sio_new_bldg_SSP5 = determine_inflow_outflow_new_bldg('S_timber_high',FA_dsm_SSP=FA_dsm_SSP5, lt=lt_future, plot=False, plot_title='SSP5 ')

## Check to see if stocks match:
# check to see if how much the inflow, outflow, and stocks differ from the original stock-driven model
check_df_stock = pd.DataFrame({
    'existing_stock': os_existing_SSP1.loc[2017:]['total_stock'],
    'new_stock': sio_new_bldg_SSP1.loc[2017:]['total_stock'],
    'sum_stock': os_existing_SSP1.loc[2017:]['total_stock'] + sio_new_bldg_SSP1.loc[2017:]['total_stock'],
    'correct_stock': FA_dsm_SSP1.loc[2017:]['stock_total'],
    'percent_difference': (FA_dsm_SSP1.loc[2017:]['stock_total'] - (os_existing_SSP1.loc[2017:]['total_stock'] + sio_new_bldg_SSP1.loc[2017:]['total_stock'])) / FA_dsm_SSP1.loc[2017:]['stock_total']
})
check_df_inflow = pd.DataFrame({
    'new_inflow': sio_new_bldg_SSP1.loc[2017:]['total_inflow'],
    'correct_inflow': FA_dsm_SSP1.loc[2017:]['inflow_total'],
    'difference': sio_new_bldg_SSP1.loc[2017:]['total_inflow'] - FA_dsm_SSP1.loc[2017:]['inflow_total']
})
check_df_outflow = pd.DataFrame({
    'existing_outflow': os_existing_SSP1.loc[2017:]['total_outflow'],
    'new_outflow': sio_new_bldg_SSP1.loc[2017:]['total_outflow'],
    'correct_outflow': FA_dsm_SSP1.loc[2017:]['outflow_total'],
    'percent_difference': (os_existing_SSP1.loc[2017:]['total_outflow'] + sio_new_bldg_SSP1.loc[2017:]['total_outflow'] - FA_dsm_SSP1.loc[2017:]['outflow_total']) / FA_dsm_SSP1.loc[2017:]['outflow_total']
})
# print results of the check
print('Mean percent difference in stock is = ' + str(np.mean(check_df_stock['percent_difference']) * 100 ) + '%')
print('Mean  difference in inflow is = ' + str(np.mean(check_df_inflow['difference'])))
print('Mean percent difference in outflow is = ' + str(np.mean(check_df_outflow['percent_difference']) * 100 ) + '%')

# # ------------------------------------------------------------------------------------
# add together the two sub DSM models for total area flows in for 2017 to 2100
area_stock_2017_2100_SSP1 = pd.DataFrame({
    'stock_all': os_existing_SSP1.loc[2017:]['total_stock'] + sio_new_bldg_SSP1.loc[2017:]['total_stock'],
    'stock_LF_wood': os_existing_SSP1.loc[2017:]['stock_LF_wood'] + sio_new_bldg_SSP1.loc[2017:]['stock_LF_wood'],
    'stock_Mass_Timber': os_existing_SSP1.loc[2017:]['stock_Mass_Timber'] + sio_new_bldg_SSP1.loc[2017:]['stock_Mass_Timber'],
    'stock_Steel': os_existing_SSP1.loc[2017:]['stock_Steel'] + sio_new_bldg_SSP1.loc[2017:]['stock_Steel'],
    'stock_RC': os_existing_SSP1.loc[2017:]['stock_RC'] + sio_new_bldg_SSP1.loc[2017:]['stock_RC'],
    'stock_RM': os_existing_SSP1.loc[2017:]['stock_RM'] + sio_new_bldg_SSP1.loc[2017:]['stock_RM'],
    'stock_URM': os_existing_SSP1.loc[2017:]['stock_URM'] + sio_new_bldg_SSP1.loc[2017:]['stock_URM'],
    'stock_MH': os_existing_SSP1.loc[2017:]['stock_MH'] + sio_new_bldg_SSP1.loc[2017:]['stock_MH']
})
area_inflow_2017_2100_SSP1 = pd.DataFrame({
    'inflow_all': sio_new_bldg_SSP1.loc[2017:]['total_inflow'],
    'inflow_LF_wood': sio_new_bldg_SSP1.loc[2017:]['inflow_LF_wood'],
    'inflow_Mass_Timber': sio_new_bldg_SSP1.loc[2017:]['inflow_Mass_Timber'],
    'inflow_Steel': sio_new_bldg_SSP1.loc[2017:]['inflow_Steel'],
    'inflow_RC': sio_new_bldg_SSP1.loc[2017:]['inflow_RC'],
    'inflow_RM': sio_new_bldg_SSP1.loc[2017:]['inflow_RM'],
    'inflow_URM': sio_new_bldg_SSP1.loc[2017:]['inflow_URM'],
    'inflow_MH': sio_new_bldg_SSP1.loc[2017:]['inflow_MH']
})
area_outflow_2017_2100_SSP1 = pd.DataFrame({
    'outflow_all': os_existing_SSP1.loc[2017:]['total_outflow'] + sio_new_bldg_SSP1.loc[2017:]['total_outflow'],
    'outflow_LF_wood': os_existing_SSP1.loc[2017:]['outflow_LF_wood'] + sio_new_bldg_SSP1.loc[2017:]['outflow_LF_wood'],
    'outflow_Mass_Timber': os_existing_SSP1.loc[2017:]['outflow_Mass_Timber'] + sio_new_bldg_SSP1.loc[2017:]['outflow_Mass_Timber'],
    'outflow_Steel': os_existing_SSP1.loc[2017:]['outflow_Steel'] + sio_new_bldg_SSP1.loc[2017:]['outflow_Steel'],
    'outflow_RC': os_existing_SSP1.loc[2017:]['outflow_RC'] + sio_new_bldg_SSP1.loc[2017:]['outflow_RC'],
    'outflow_RM': os_existing_SSP1.loc[2017:]['outflow_RM'] + sio_new_bldg_SSP1.loc[2017:]['outflow_RM'],
    'outflow_URM': os_existing_SSP1.loc[2017:]['outflow_URM'] + sio_new_bldg_SSP1.loc[2017:]['outflow_URM'],
    'outflow_MH': os_existing_SSP1.loc[2017:]['outflow_MH'] + sio_new_bldg_SSP1.loc[2017:]['outflow_MH']
})


## Next steps
# - compute material inflows and material outflows from floor areas.
# # ------------------------------------------------------------------------------------
# compute the total mass flows



# # -------------------------------------------------------------------------------------------------------------------

# Calculate material demand by structural system

# Inflow of materials in (unit = Megaton, Mt)
inflow_mat = pd.DataFrame()
inflow_mat['LF_wood_steel'] = area_inflow_2017_2100_SSP1['inflow_LF_wood'] * materials_intensity_df['LF_wood']['Steel_kgm2_mean'] * 10e6 / 10e9
inflow_mat['LF_wood_conc'] = area_inflow_2017_2100_SSP1['inflow_LF_wood'] * materials_intensity_df['LF_wood']['Concrete_kgm2_mean'] * 10e6 / 10e9
inflow_mat['LF_wood_engwood'] = area_inflow_2017_2100_SSP1['inflow_LF_wood'] * materials_intensity_df['LF_wood']['Eng_wood_kgm2_mean'] * 10e6 / 10e9
inflow_mat['LF_wood_dimlum'] = area_inflow_2017_2100_SSP1['inflow_LF_wood'] * materials_intensity_df['LF_wood']['Dim_lumber_kgm2_mean'] * 10e6 / 10e9
inflow_mat['LF_wood_masonry'] = area_inflow_2017_2100_SSP1['inflow_LF_wood'] * materials_intensity_df['LF_wood']['Masonry_kgm2_mean'] * 10e6 / 10e9

inflow_mat['Mass_Timber_steel'] = area_inflow_2017_2100_SSP1['inflow_Mass_Timber'] * materials_intensity_df['Mass_Timber']['Steel_kgm2_mean'] * 10e6 / 10e9
inflow_mat['Mass_Timber_conc'] = area_inflow_2017_2100_SSP1['inflow_Mass_Timber'] * materials_intensity_df['Mass_Timber']['Concrete_kgm2_mean'] * 10e6 / 10e9
inflow_mat['Mass_Timber_engwood'] = area_inflow_2017_2100_SSP1['inflow_Mass_Timber'] * materials_intensity_df['Mass_Timber']['Eng_wood_kgm2_mean'] * 10e6 / 10e9
inflow_mat['Mass_Timber_dimlum'] = area_inflow_2017_2100_SSP1['inflow_Mass_Timber'] * materials_intensity_df['Mass_Timber']['Dim_lumber_kgm2_mean'] * 10e6 / 10e9
inflow_mat['Mass_Timber_masonry'] = area_inflow_2017_2100_SSP1['inflow_Mass_Timber'] * materials_intensity_df['Mass_Timber']['Masonry_kgm2_mean'] * 10e6 / 10e9

inflow_mat['Steel_steel'] = area_inflow_2017_2100_SSP1['inflow_Steel'] * materials_intensity_df['Steel']['Steel_kgm2_mean'] * 10e6 / 10e9
inflow_mat['Steel_conc'] = area_inflow_2017_2100_SSP1['inflow_Steel'] * materials_intensity_df['Steel']['Concrete_kgm2_mean'] * 10e6 / 10e9
inflow_mat['Steel_engwood'] = area_inflow_2017_2100_SSP1['inflow_Steel'] * materials_intensity_df['Steel']['Eng_wood_kgm2_mean'] * 10e6 / 10e9
inflow_mat['Steel_dimlum'] = area_inflow_2017_2100_SSP1['inflow_Steel'] * materials_intensity_df['Steel']['Dim_lumber_kgm2_mean'] * 10e6 / 10e9
inflow_mat['Steel_masonry'] = area_inflow_2017_2100_SSP1['inflow_Steel'] * materials_intensity_df['Steel']['Masonry_kgm2_mean'] * 10e6 / 10e9

inflow_mat['RC_steel'] = area_inflow_2017_2100_SSP1['inflow_RC'] * materials_intensity_df['RC']['Steel_kgm2_mean'] * 10e6 / 10e9
inflow_mat['RC_conc'] = area_inflow_2017_2100_SSP1['inflow_RC'] * materials_intensity_df['RC']['Concrete_kgm2_mean'] * 10e6 / 10e9
inflow_mat['RC_engwood'] = area_inflow_2017_2100_SSP1['inflow_RC'] * materials_intensity_df['RC']['Eng_wood_kgm2_mean'] * 10e6 / 10e9
inflow_mat['RC_dimlum'] = area_inflow_2017_2100_SSP1['inflow_RC'] * materials_intensity_df['RC']['Dim_lumber_kgm2_mean'] * 10e6 / 10e9
inflow_mat['RC_masonry'] = area_inflow_2017_2100_SSP1['inflow_RC'] * materials_intensity_df['RC']['Masonry_kgm2_mean'] * 10e6 / 10e9

inflow_mat['RM_steel'] = area_inflow_2017_2100_SSP1['inflow_RM'] * materials_intensity_df['RM']['Steel_kgm2_mean'] * 10e6 / 10e9
inflow_mat['RM_conc'] = area_inflow_2017_2100_SSP1['inflow_RM'] * materials_intensity_df['RM']['Concrete_kgm2_mean'] * 10e6 / 10e9
inflow_mat['RM_engwood'] = area_inflow_2017_2100_SSP1['inflow_RM'] * materials_intensity_df['RM']['Eng_wood_kgm2_mean'] * 10e6 / 10e9
inflow_mat['RM_dimlum'] = area_inflow_2017_2100_SSP1['inflow_RM'] * materials_intensity_df['RM']['Dim_lumber_kgm2_mean'] * 10e6 / 10e9
inflow_mat['RM_masonry'] = area_inflow_2017_2100_SSP1['inflow_RM'] * materials_intensity_df['RM']['Masonry_kgm2_mean'] * 10e6 / 10e9

inflow_mat['URM_steel'] = area_inflow_2017_2100_SSP1['inflow_URM'] * materials_intensity_df['URM']['Steel_kgm2_mean'] * 10e6 / 10e9
inflow_mat['URM_conc'] = area_inflow_2017_2100_SSP1['inflow_URM'] * materials_intensity_df['URM']['Concrete_kgm2_mean'] * 10e6 / 10e9
inflow_mat['URM_engwood'] = area_inflow_2017_2100_SSP1['inflow_URM'] * materials_intensity_df['URM']['Eng_wood_kgm2_mean'] * 10e6 / 10e9
inflow_mat['URM_dimlum'] = area_inflow_2017_2100_SSP1['inflow_URM'] * materials_intensity_df['URM']['Dim_lumber_kgm2_mean'] * 10e6 / 10e9
inflow_mat['URM_masonry'] = area_inflow_2017_2100_SSP1['inflow_URM'] * materials_intensity_df['URM']['Masonry_kgm2_mean'] * 10e6 / 10e9

# inflow_mat['MH_steel'] = area_inflow_2017_2100_SSP1['MH_i'] * materials_intensity_df['MH']['Steel_kgm2_mean'] * 10e6 / 10e9
# inflow_mat['MH_conc'] = area_inflow_2017_2100_SSP1['MH_i'] * materials_intensity_df['MH']['Concrete_kgm2_mean'] * 10e6 / 10e9
# inflow_mat['MH_engwood'] = area_inflow_2017_2100_SSP1['MH_i'] * materials_intensity_df['MH']['Eng_wood_kgm2_mean'] * 10e6 / 10e9
# inflow_mat['MH_dimlum'] = area_inflow_2017_2100_SSP1['MH_i'] * materials_intensity_df['MH']['Dim_lumber_kgm2_mean'] * 10e6 / 10e9
# inflow_mat['MH_masonry'] = area_inflow_2017_2100_SSP1['MH_i'] * materials_intensity_df['MH']['Masonry_kgm2_mean'] * 10e6 / 10e9

# Total inflows of each material (by structure type), unit = Mt
steel_tot_inflow = inflow_mat.filter(regex='_steel', axis=1)
conc_tot_inflow = inflow_mat.filter(regex='_conc', axis=1)
engwood_tot_inflow = inflow_mat.filter(regex='_engwood', axis=1)
dimlum_tot_inflow = inflow_mat.filter(regex='_dimlum', axis=1)
masonry_tot_inflow = inflow_mat.filter(regex='_masonry', axis=1)
# adding in a sum row for each year
steel_tot_inflow['Sum'] = steel_tot_inflow.sum(axis=1)
conc_tot_inflow['Sum'] = conc_tot_inflow.sum(axis=1)
engwood_tot_inflow['Sum'] = engwood_tot_inflow.sum(axis=1)
dimlum_tot_inflow['Sum'] = dimlum_tot_inflow.sum(axis=1)
masonry_tot_inflow['Sum'] = masonry_tot_inflow.sum(axis=1)

# print the material demand for a particular year
year = 2020
print('Total steel demand in ', str(year),  ' =   ', steel_tot_inflow['Sum'][year], ' Mt')
print('Total concrete demand in ', str(year),  ' =   ', conc_tot_inflow['Sum'][year], ' Mt')
print('Total engineered wood demand in ', str(year),  ' =   ', engwood_tot_inflow['Sum'][year], ' Mt')
print('Total dimensioned lumber demand in ', str(year),  ' =   ', dimlum_tot_inflow['Sum'][year], ' Mt')
print('Total masonry demand in ', str(year),  ' =   ', masonry_tot_inflow['Sum'][year], ' Mt')



# plot total material demand each year (Mt)
fig, axs = plt.subplots(3, 2)
axs[0, 0].plot(steel_tot_inflow.index, steel_tot_inflow.Sum)
axs[0, 0].plot([2017, 2017], [0, 1.2*steel_tot_inflow.Sum.max()], color='k', LineStyle='--')
axs[0, 0].set_title('Steel')
axs[0, 0].set_xlim(2000)

axs[0, 1].plot(conc_tot_inflow.index, conc_tot_inflow.Sum, 'tab:orange')
axs[0, 1].plot([2017, 2017], [0, 1.2*conc_tot_inflow.Sum.max()], color='k', LineStyle='--')
axs[0, 1].set_title('Concrete')
axs[0, 1].set_xlim(2000)

axs[1, 0].plot(engwood_tot_inflow.index, engwood_tot_inflow.Sum, 'tab:green')
axs[1, 0].plot([2017, 2017], [0, 1.2*engwood_tot_inflow.Sum.max()], color='k', LineStyle='--')
axs[1, 0].set_title('Engineered Wood')
axs[1, 0].set_xlim(2000)

axs[1, 1].plot(dimlum_tot_inflow.index, dimlum_tot_inflow.Sum, 'tab:red')
axs[1, 1].plot([2017, 2017], [0, 1.2*dimlum_tot_inflow.Sum.max()], color='k', LineStyle='--')
axs[1, 1].set_title('Dimensioned Lumber')
axs[1, 1].set_xlim(2000)

axs[2, 0].plot(masonry_tot_inflow.index, masonry_tot_inflow.Sum, 'tab:purple')
axs[2, 0].plot([2017, 2017], [0, 1.2*masonry_tot_inflow.Sum.max()], color='k', LineStyle='--')
axs[2, 0].set_title('Masonry')
axs[2, 0].set_xlim(2000)
# delete the sixth space
fig.delaxes(axs[2,1])
# add ylabels
for ax in axs.flat:
    ax.set(ylabel='Mt/year')
fig.show()




## ---------------------- OLD CODE ----------------------
# Calculate historical floor area inflow/outflow by structural system (unit = million m2)
# sio_area_by_ss_1820_2020 = pd.DataFrame()
# sio_area_by_ss_1820_2020['LF_wood_s'] = total_area.loc[0:2020, 'stock_total'] * structure_data_historical.LF_wood[0]
# sio_area_by_ss_1820_2020['LF_wood_i'] = total_area.loc[0:2020, 'inflow_total'] * structure_data_historical.LF_wood[0]
# sio_area_by_ss_1820_2020['LF_wood_o'] = total_area.loc[0:2020, 'outflow_total'] * structure_data_historical.LF_wood[0]
# sio_area_by_ss_1820_2020['Mass_Timber_s'] = total_area.loc[0:2020, 'stock_total'] * structure_data_historical.Mass_Timber[0]
# sio_area_by_ss_1820_2020['Mass_Timber_i'] = total_area.loc[0:2020, 'inflow_total'] * structure_data_historical.Mass_Timber[0]
# sio_area_by_ss_1820_2020['Mass_Timber_o'] = total_area.loc[0:2020, 'outflow_total'] * structure_data_historical.Mass_Timber[0]
# sio_area_by_ss_1820_2020['Steel_s'] = total_area.loc[0:2020, 'stock_total'] * structure_data_historical.Steel[0]
# sio_area_by_ss_1820_2020['Steel_i'] = total_area.loc[0:2020, 'inflow_total'] * structure_data_historical.Steel[0]
# sio_area_by_ss_1820_2020['Steel_o'] = total_area.loc[0:2020, 'outflow_total'] * structure_data_historical.Steel[0]
# sio_area_by_ss_1820_2020['RC_s'] = total_area.loc[0:2020, 'stock_total'] * structure_data_historical.RC[0]
# sio_area_by_ss_1820_2020['RC_i'] = total_area.loc[0:2020, 'inflow_total'] * structure_data_historical.RC[0]
# sio_area_by_ss_1820_2020['RC_o'] = total_area.loc[0:2020, 'outflow_total'] * structure_data_historical.RC[0]
# sio_area_by_ss_1820_2020['RM_s'] = total_area.loc[0:2020, 'stock_total'] * structure_data_historical.RM[0]
# sio_area_by_ss_1820_2020['RM_i'] = total_area.loc[0:2020, 'inflow_total'] * structure_data_historical.RM[0]
# sio_area_by_ss_1820_2020['RM_o'] = total_area.loc[0:2020, 'outflow_total'] * structure_data_historical.RM[0]
# sio_area_by_ss_1820_2020['URM_s'] = total_area.loc[0:2020, 'stock_total'] * structure_data_historical.URM[0]
# sio_area_by_ss_1820_2020['URM_i'] = total_area.loc[0:2020, 'inflow_total'] * structure_data_historical.URM[0]
# sio_area_by_ss_1820_2020['URM_o'] = total_area.loc[0:2020, 'outflow_total'] * structure_data_historical.URM[0]
# sio_area_by_ss_1820_2020['MH_s'] = total_area.loc[0:2020, 'stock_total'] * structure_data_historical.MH[0]
# sio_area_by_ss_1820_2020['MH_i'] = total_area.loc[0:2020, 'inflow_total'] * structure_data_historical.MH[0]
# sio_area_by_ss_1820_2020['MH_o'] = total_area.loc[0:2020, 'outflow_total'] * structure_data_historical.MH[0]

# Calculate future floor area inflow/outflow by structural system (unit = million m2)
# sio_area_by_ss_2020_2100 = pd.DataFrame()
# sio_area_by_ss_2020_2100['LF_wood_s'] = total_area.loc[2021:2100, 'stock_total'] * structure_data_historical.LF_wood[0]
# sio_area_by_ss_2020_2100['LF_wood_i'] = total_area.loc[2021:2100, 'inflow_total'] * structure_data_historical.LF_wood[0]
# sio_area_by_ss_2020_2100['LF_wood_o'] = total_area.loc[2021:2100, 'outflow_total'] * structure_data_historical.LF_wood[0]
# sio_area_by_ss_2020_2100['Mass_Timber_s'] = total_area.loc[2021:2100, 'stock_total'] * structure_data_historical.Mass_Timber[0]
# sio_area_by_ss_2020_2100['Mass_Timber_i'] = total_area.loc[2021:2100, 'inflow_total'] * structure_data_historical.Mass_Timber[0]
# sio_area_by_ss_2020_2100['Mass_Timber_o'] = total_area.loc[2021:2100, 'outflow_total'] * structure_data_historical.Mass_Timber[0]
# sio_area_by_ss_2020_2100['Steel_s'] = total_area.loc[2021:2100, 'stock_total'] * structure_data_historical.Steel[0]
# sio_area_by_ss_2020_2100['Steel_i'] = total_area.loc[2021:2100, 'inflow_total'] * structure_data_historical.Steel[0]
# sio_area_by_ss_2020_2100['Steel_o'] = total_area.loc[2021:2100, 'outflow_total'] * structure_data_historical.Steel[0]
# sio_area_by_ss_2020_2100['RC_s'] = total_area.loc[2021:2100, 'stock_total'] * structure_data_historical.RC[0]
# sio_area_by_ss_2020_2100['RC_i'] = total_area.loc[2021:2100, 'inflow_total'] * structure_data_historical.RC[0]
# sio_area_by_ss_2020_2100['RC_o'] = total_area.loc[2021:2100, 'outflow_total'] * structure_data_historical.RC[0]
# sio_area_by_ss_2020_2100['RM_s'] = total_area.loc[2021:2100, 'stock_total'] * structure_data_historical.RM[0]
# sio_area_by_ss_2020_2100['RM_i'] = total_area.loc[2021:2100, 'inflow_total'] * structure_data_historical.RM[0]
# sio_area_by_ss_2020_2100['RM_o'] = total_area.loc[2021:2100, 'outflow_total'] * structure_data_historical.RM[0]
# sio_area_by_ss_2020_2100['URM_s'] = total_area.loc[2021:2100, 'stock_total'] * structure_data_historical.URM[0]
# sio_area_by_ss_2020_2100['URM_i'] = total_area.loc[2021:2100, 'inflow_total'] * structure_data_historical.URM[0]
# sio_area_by_ss_2020_2100['URM_o'] = total_area.loc[2021:2100, 'outflow_total'] * structure_data_historical.URM[0]
# sio_area_by_ss_2020_2100['MH_s'] = total_area.loc[2021:2100, 'stock_total'] * structure_data_historical.MH[0]
# sio_area_by_ss_2020_2100['MH_i'] = total_area.loc[2021:2100, 'inflow_total'] * structure_data_historical.MH[0]
# sio_area_by_ss_2020_2100['MH_o'] = total_area.loc[2021:2100, 'outflow_total'] * structure_data_historical.MH[0]


