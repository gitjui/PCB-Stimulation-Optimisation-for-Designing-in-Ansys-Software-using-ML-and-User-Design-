import json
import numpy as np
import os
import random
import pickle
import shutil
from utils_double import run


# 定义搜寻范围
def searching_boundary():
    # partition the space into several sub-parts to parallely implement in different PC
    w1_bound = [1.0, 3.0]       # mm
    k_bound = [1.09, 1.115]        # 
    space_bound = [2.0, 4.0]    # mm
    n_bounds = [15, 25]          # 
    return w1_bound, k_bound, space_bound, n_bounds

# 把几何参数导入到json文件中
def convert_to_config(w1, k, space, n, save_dir, index=""):
    config_file = "config_template.json" # a template config file
    with open(config_file, "r+") as f:
        kwargs = json.load(f)
    kwargs["w1"] = w1
    kwargs["space"] = space
    w = [w1 / (k ** i) for i in range(0, n)]
    rout = 99 # mm
    kwargs["w"] = w   
    kwargs["rout"] = rout
    kwargs["k"] = k
    kwargs["n"] = n
    kwargs["res_path"] = save_dir
    config_file = f'{save_dir}/config{index}.json'
    # print(config_file)
    # print(kwargs)
    with open(config_file, 'w+') as f:
        json.dump(kwargs, f)
    return config_file

# 随机得到一组几何参数值
def get_random():
    w1_bound, k_bound, space_bound, n_bounds = searching_boundary()
    w1 = random.uniform(*w1_bound)
    k = random.uniform(*k_bound)
    space = random.uniform(*space_bound)
    n = random.sample(list(range(n_bounds[0], n_bounds[1]+1)), 1)[0]
    return w1, k, space, n

# 判定rin会不会小于10mm
def check_rad(config_file):
    with open(config_file, "r+") as f:
        kwargs = json.load(f)
    w = kwargs["w"]
    radins = [kwargs["rout"]-w[0]]
    for i in range(1, len(w)):
        current_w = w[i]
        radin = radins[-1] - kwargs["space"] - current_w
        radins.append(radin)
        
    if radins[-1] <= 10: # rin小于0不合理，给一个设定范围作为保护
        return False
    return True

# 用拉丁超立方方法搜寻
def latin(SRF_ref, num=200, restore=False):
    check_point_file = "./checkpoint.pickle"
    if restore:
        assert os.path.exists(check_point_file), "the checkpoint does not exist, please rerun"
    
    # define the boundaries
    bounds = [*searching_boundary()]
    # define whether the variable is categorical or not
    is_cat = [False]*3+[True]   # 列表用于标记哪些参数是离散的（第4个参数 n 是离散的）
    
    d = 1.0 / num
    D = 4   # 五个维度
    # 创建用于保存仿真结果的目录
    save_dir = "./latin"            # EXTENSION
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    results = {key:{"obj": None, "all": None} for key in range(num)}
    if not restore:
        params = [[] for _ in range(num)]   # 创建一个列表用于存储每个参数样本，列表长度为要生成的样本数量
        # generate a batch following Latin Hypercube Search
        # 生成拉丁超立方样本
        for i in range(D):
            if not is_cat[i]:   # 连续变量
                temp = []
                for j in range(num):
                    tmp = np.random.uniform(low=j*d, high=(j+1)*d, size=1)[0]   # 计算采样范围，在范围内随机生成一个浮点数
                    tmp = tmp*(bounds[i][1]-bounds[i][0])+bounds[i][0]          # 将 [0, 1] 区间的值映射到 [bounds[i][0], bounds[i][1]] 范围中
                    temp.append(tmp)
            else:               # 离散变量
                tmp = list(range(bounds[i][0], bounds[i][1]+1))                 # 离散值的范围
                np.random.shuffle(tmp)                                          # 将 tmp 列表中的元素顺序随机打乱
                temp = [tmp[j%(bounds[i][1]-bounds[i][0]+1)] for j in range(num)]   # 分配离散值给每一个样本，通过取模运算来实现循环分配离散值
            np.random.shuffle(temp)
            for j, item in enumerate(temp): # 当前维度的采样值添加到每个样本的参数列表中
                params[j].append(item)
        j_start = 0
    else:
        with open(check_point_file, "rb") as f:
            j_start, params = pickle.load(f)
            
    # iteratively conduct ansys simulation
    for j in range(j_start, len(params)):
        with open(check_point_file, "wb+") as f:
            pickle.dump([j, params], f)
        
        w1, k, space, n = params[j]
        _j = 0  # _j 是一个计数器，用于记录当前尝试的次数。它在每次重新生成参数组合时递增。
        while True: # 确保在参数组合不符合要求或仿真失败的情况下能够重新生成参数并重新运行仿真，直到成功为止
            if _j != 0: # 当 _j != 0 时，表示之前的参数组合要么仿真失败，要么不符合要求，因此需要生成新的参数组合。
                w1 = random.uniform(*bounds[0])
                k = random.uniform(*bounds[1])
                space = random.uniform(*bounds[2])
                n = random.sample(list(range(bounds[3][0], bounds[3][1]+1)), 1)[0]
            config_file = convert_to_config(w1, k, space, n, save_dir, index=j)
            if not check_rad(config_file):  # 使用 check_rad 函数对配置文件进行初步检查，确保该参数组合符合仿真要求。
                print(f"Invalid configuration with radius < 10: {config_file}")
                _j += 1
                continue            
            cir_pcb, if_success = run(config_file, index=j)
            # cir_pcb, if_success = run(config_file, index=j)
            del_cache(config_file) # EXTENSION
            
            # if not successful, then randomly generate another design and conduct simulation again
            if not if_success:
                _j += 1
                print(cir_pcb.error_log)
                continue
            
            # save the results into the dictionary results
            obj_value = obj_func(cir_pcb.parsed_results)
            results[j]["obj"] = obj_value
            results[j]["all"] = cir_pcb.parsed_results
            break
    # save the results to the .json file
    with open(f"{save_dir}/all_results.json", "w") as f:
        json.dump(results, f)
    
    return results

# 清除缓存文件
def del_cache(file):
    with open(file, "r+") as f:
        kwargs = json.load(f)
    dir_cache = kwargs['project_path']+kwargs['project_id']+".aedtresults"
    if os.path.exists(dir_cache):
        shutil.rmtree(dir_cache)
        
# 把文件转移到特定文件夹中
def move_file(files, save_dir):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    for file in files:
        with open(file, "r+") as f:
            kwargs = json.load(f)
        shutil.move(kwargs['project_path']+kwargs['project_id']+".aedt", save_dir+"/"+kwargs['project_id']+".aedt")
        
# 计算目标函数值
def obj_func_dictsearch(parsed_results, SRF_ref=6.78, w1_penalty=1000.0, w2_penalty=200):    # EXTENSION
    SRF1, SRF2, Q = parsed_results["SRF1"], parsed_results["SRF2"], parsed_results["Q"]
    penalty1 = abs(SRF1-SRF_ref)*w1_penalty
    penalty2= (SRF2-SRF1)*w2_penalty
    # fitness value for GA
    fitness_value = Q-penalty1+penalty2
    return fitness_value

# 只优化第一个谐振频率的Q
def obj_func(parsed_results):
    Q = parsed_results["Q"]
    fitness_value = Q
    return fitness_value