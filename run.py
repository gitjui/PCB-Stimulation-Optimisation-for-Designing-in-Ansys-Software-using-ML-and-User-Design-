from utils_double import *
from optimizer import *
from dict_search import dict_search
from d2ea import optim_d2ea


# 未设置网格
if __name__ == "__main__":  # 确保这段代码只在直接运行脚本时执行，而不是在被导入时执行
    
    """Automate the simulation once with specified geometrical parameters"""
    # 调用了 convert_to_config 函数生成配置文件，然后使用 run 函数启动仿真
    w1, k, space, n, save_dir, index = 1.616, 1.03842, 2.482, 20, ".", 0
    config_file = convert_to_config(w1, k, space, n, save_dir, index=index)
    cir_pcb, if_success = run(config_file, index=index) 
    # parse results 处理结果
    print(cir_pcb.parse_results())
    
    # """Stage 1: Latin Hypercube Search"""
    # 拉丁超立方搜索
    # SRF, num = 3.054, 100
    # latin(SRF, num=num, restore=False) 
    # Below code is used instead to restore at the breakpoint in case of unexpected interruption or error
    # latin(SRF, num=num, restore=True)
    
    
    
    # """Stage 2: Dictionary search to accurately locate SRF"""
    # 用于准确定位目标共振频率（SRF）
    # target_SRF, aug_num =3.054, 100
    # prev_result_path = "latin"
    # dict_search(aug_num, target_SRF, prev_result_path, num=20, threshold=0.5, weight=10.0, restore=False)
    # Below code is used instead to restore at the breakpoint in case of unexpected interruption or error
    # dict_search(aug_num, target_SRF, prev_result_path, num=20, threshold=0.5, weight=10.0, restore=True)
    
    # Stage 3: TT-DDEA to boost the quality factor with required SRF
    # 使用 TT-DDEA 优化质量因数，同时满足指定的共振频率
    # stage1_folder = "latin"
    # stage2_folder = "latin/dict_search"
    # epoch, target_SRF = 100, 3.03
    # optim_d2ea(stage1_folder, stage2_folder, epoch, target_SRF, restore=False, standardize=True)
    # optim_d2ea(stage1_folder, epoch, target_SRF, restore=False, standardize=True)
    # # Below code is used instead to restore at the breakpoint in case of unexpected interruption or error
    # # optim_d2ea(stage1_folder, stage2_folder, epoch, target_SRF, restore=True, standardize=True)