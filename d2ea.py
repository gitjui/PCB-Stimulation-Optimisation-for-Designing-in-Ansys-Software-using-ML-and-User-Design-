import numpy as np
import time
import os
import re
import json
import pickle
from D2EA import RBFN
from D2EA import GA
from utils_double import IPTCoil
from D2EA import *
from tqdm import tqdm
from utils_double import run
from dict_search import get_x, get_y
from optimizer import convert_to_config, del_cache, obj_func

def load_all(paths):
    all_results = {}
    i = 0
    if type(paths) == str:
        paths = paths
    for path in paths:
        try:
            files = os.listdir(path)
            f = re.compile(r"config(\d+).json")
            indices = [int(f.match(file)[1]) for file in files if f.match(file)]
            for idx in indices:
                file_names = lambda idx: [f"config{idx}.json", f"index{idx}-dB20Z-Stage0.csv",
                                          f"index{idx}-dB20Z-Stage1.csv"]
                file_full = os.path.join(path, file_names(idx)[0])
                files_full = [os.path.join(path, file) for file in file_names(idx)[1:]]
                with open(file_full, "r") as f:
                    kwargs = json.load(f)
                cir_pcb = IPTCoil(kwargs, None)
                cir_pcb.report_files.extend(files_full)
                cir_pcb.parse_results()
                all_results[i] = {"kwargs": kwargs, "results": cir_pcb.parsed_results, "config": file_full}
                del cir_pcb
                i += 1
        except Exception as e:
            print(e)
    return all_results

def save_data_d2ea(basepath, folders):
    # get the path of all folders
    folders = [os.path.join(basepath, path) for path in folders]
    # load all results
    all_results = load_all(folders)

    # select the features as inputs and objectives as outputs
    all_results_x = np.array([get_x(all_results[key]['kwargs']) for key in all_results])[:, [1, 2, 4, 5]] # w1, k, n, space
    all_results_y = np.array([get_y(all_results[key]['results'])[0] for key in all_results]) # SRF
    all_results_y2 = np.array([get_y(all_results[key]['results'])[1] for key in all_results]) # Q
    
    # 使用3σ原则，筛选掉偏离平均值超过3倍标准差的数据（异常点）
    idx = (np.abs(all_results_y-all_results_y.mean())<=3*all_results_y.std()) & \
            (np.abs(all_results_y2-all_results_y2.mean())<=3*all_results_y2.std())
    all_results_x = all_results_x[idx]
    all_results_y = all_results_y[idx]
    all_results_y2 = all_results_y2[idx]
    
    # save files for training
    np.savetxt("D2EA/Data/x.csv", all_results_x, delimiter=",") # EXTENSION
    np.savetxt("D2EA/Data/y.csv", all_results_y, delimiter=",") # EXTENSION
    np.savetxt("D2EA/Data/y2.csv", all_results_y2, delimiter=",") # EXTENSION
    
def d2ea(target_SRF, standardize=True):
    starttime = time.perf_counter()
    
    # hyperparameters for the d2ea algorithm
    dimension = 4
    lower_bound = 0.0 # EXTENSION
    upper_bound = 1.0 # EXTENSION
    # load data for training
    x_path = "D2EA/Data/x.csv" # EXTENSION
    y_path = "D2EA/Data/y.csv" # EXTENSION
    y2_path = "D2EA/Data/y2.csv" # EXTENSION
    x = np.loadtxt(x_path, delimiter=",")
    y = np.loadtxt(y_path, delimiter=",")
    y2 = np.loadtxt(y2_path, delimiter=",")
    
    # standardize the inputs and outputs
    if standardize:
        # 将输入数据 x 的每一列（每个特征）压缩到 [0, 1] 的范围
        x_max = x.max(axis=0)
        x_min = x.min(axis=0)
        x = (x-x_min)/(x_max-x_min)
        # 将输出数据（y 和 y2）标准化为标准正态分布（均值为 0，标准差为 1）
        y_mean = y.mean()
        y_std = y.std()
        y2_mean = y2.mean()
        y2_std = y2.std()
        y = (y-y_mean)/y_std
        y2 = (y-y2_mean)/y2_std
    
    # define three RBFN models
    datanum = len(x)    # 总数据点数量，即输入特征 x 的样本数
    model = [0] * 3     # 用于存储 3 个独立的 RBFN 模型
    traindata = int(datanum / 3)    # 此处将数据点总数均分为三份，用于初始化三层不同的 RBFN 模型
    model[0] = RBFN(input_shape=dimension, hidden_shape=int(np.sqrt(traindata)), kernel='gaussian') # 隐层神经元数量，取训练样本数量的平方根
    model[1] = RBFN(input_shape=dimension, hidden_shape=int(np.sqrt(traindata)), kernel='gaussian')
    model[2] = RBFN(input_shape=dimension, hidden_shape=int(np.sqrt(traindata)), kernel='gaussian')
    numxy = resetmodel(x,y,model)   # 使用输入x和目标值y对三个RBFN模型进行训练
    
    model2 = [0] * 3
    model2[0] = RBFN(input_shape=dimension, hidden_shape=int(np.sqrt(traindata)), kernel='gaussian')
    model2[1] = RBFN(input_shape=dimension, hidden_shape=int(np.sqrt(traindata)), kernel='gaussian')
    model2[2] = RBFN(input_shape=dimension, hidden_shape=int(np.sqrt(traindata)), kernel='gaussian')
    numxy2 = resetmodel(x,y2,model2)

    # define the genetic algorithm
    max_iter = 100  # 最大迭代次数
    # pop_size种群大小，越大解的多样性越高
    ga = GA(pop_size=100, dimension=dimension, lower_bound=lower_bound, upper_bound=upper_bound)
    ga.init_Population()
    
    # iteratively update model and generate new population
    for i in range(max_iter):
        # retrain the models
        # 用于使用当前种群 ga.pop 对 RBFN 模型重新训练
        updatemodel(ga.pop, numxy, model)
        updatemodel(ga.pop, numxy2, model2)
        # generate a new population 
        ga.crossover(ga.pc)     # 执行交叉操作
        ga.mutation(ga.pm)      # 执行变异操作
        ga.pop = np.unique(ga.pop, axis=0)  # 去除种群中的重复解
        # compute the fitness value from the trained RBFN models
        for j in range(0, 3):   # 遍历 3 个独立的 RBFN 模型
            temp = model[j].predict(ga.pop)     # 表示每个种群个体对应的目标 1 值
            temp2 = model2[j].predict(ga.pop)   # 表示每个种群个体对应的目标 2 值
            # 将标准化后的预测值还原到原始目标函数的数值范围
            if standardize: 
                temp = temp*y_std+y_mean
                temp2 = temp2*y2_std+y2_mean
            
            index = np.abs(temp-target_SRF) >= 0.05  # 选择偏差>0.05的点，后续惩罚
            temp2 = -temp2  # 希望最小化目标2
            temp2[index] = 100  # 偏差大的解直接设定为100
            # temp2[~index] += np.abs(temp[~index]-target_SRF)*100 # EXTENSION
            if j == 0:
                fit_value = temp2   # 第一个模型直接将temp2作为fit_value
            else:   
                fit_value = fit_value + temp2   # 后续累加
        fit_value = fit_value.reshape((len(ga.pop), 1)) # 转化为二维数组，便于后续GA处理
        # print(f"Epoch {i}: ", f"{np.mean(fit_value):.2f}", f"{np.mean(temp):.2f}", f"{np.mean(temp2):.2f}")
        # print(f"Epoch {i}-Best: ", f"{np.min(fit_value):.2f}")
        ga.selection(fit_value)     # 根据适应度值 fit_value，从当前种群中选择下一代种群，保留表现较好的个体
        updatemodel(ga.pop, numxy, model)
        updatemodel(ga.pop, numxy2, model2)

    optimum = ga.first[-1]  # 提取最优解
    endtime = time.perf_counter()   # 记录运行时间
    
    if standardize:
        optimum = optimum*(x_max-x_min)+x_min   # 还原最优解
    
    print('Optimal solution :', optimum)
    print('Execution Time :', endtime - starttime)
    return optimum

def optim_d2ea(stage1_folder, stage2_folder, 
               epoch, target_SRF, 
               check_point_file="./checkpoint-d2ea.pickle", 
               restore=False, standardize=True):
# def optim_d2ea(stage1_folder, epoch, target_SRF, 
#                check_point_file="./checkpoint-d2ea.pickle", 
#                restore=False, standardize=True):
    if restore:
        assert os.path.exists(check_point_file), "the checkpoint does not exist, please rerun"
    
    # stage1_folder = "latin"
    # stage2_folder = "latin/dict_search"
    stage3_folder = "D2EA/d2ea"
    if not os.path.exists(stage3_folder):
        os.makedirs(stage3_folder)
        
    if restore:
        with open(check_point_file, "rb") as f:
            e_start = pickle.load(f)[0]
    else:
        e_start = 0
        
    results = {key:{"obj": None, "all": None} for key in range(epoch)}
    # iteratively conduct the d2ea algorithm to optimize the design
    for e in tqdm(range(e_start, epoch)):   # 终端会显示一个动态更新的进度条
        with open(check_point_file, "wb+") as f:
            pickle.dump([e], f)
        
        print("*"*81)
        print(f"START: This is the {e}th epoch.")
        # generate data for the training of data-driven models
        folders = [stage1_folder, stage3_folder]
        save_data_d2ea(".", folders)
        print("PROCESS: Data has been saved.")
        
        # conduct optimization via d2ea
        optimum = d2ea(target_SRF, standardize=True)
        print("PROCESS: pseudo-optimal candidates have been generated.")
        
        # perform simulation on the searched optimal design from d2ea
        w1, k, n, space = list(map(lambda x: float(x), optimum))    # 将optimum中的每个元素转化为float后解包成四个变量
        n = round(n)    # 取整
        
        print("PROCESS: start to run Ansys simulation.")
        config_file = convert_to_config(w1, k, space, n, stage3_folder, index=e)
        print(config_file, e)
        cir_pcb, if_success = run(config_file, index=e)
        del_cache(config_file) # EXTENSION
        if not if_success:
            print(cir_pcb.error_log)
            continue
        else:
            cir_pcb.parse_results()
        # compute objective value and store in the results
        obj_value = obj_func(cir_pcb.parsed_results, SRF_ref=target_SRF) # EXTENTION
        # 可以修改
        results[e]["obj"] = obj_value
        results[e]["all"] = cir_pcb.parsed_results
        print(f"RESULTS: all objective values: {cir_pcb.parsed_results}")
    with open(f"{stage3_folder}/all_results.json", "w") as f:
        json.dump(results, f)