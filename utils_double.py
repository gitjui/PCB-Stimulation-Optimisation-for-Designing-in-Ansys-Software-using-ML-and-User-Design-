import numpy as np
import json
from scipy.signal import argrelextrema
from pyaedt import Hfss, Desktop
import time

class IPTCoil(object):
    def __init__(self, kwargs, ansys_handles, index=None):
        super(IPTCoil, self).__init__()
        self.kwargs = kwargs	# 参数
        self.index = index		# 第几次仿真
        self.obj_names = {"RegularPolyhedron":[{"Board": []}, 1],
                          "Polygon":[{"Coil":[]},1],
                          "Rectangle":[{"Gap":[]},1],
                          "Polyline": [{"Connector": []}, 1],
                          "Exitation":[{"Exitation":[]},2],
                          "SecondPCB":[{"Second":[]},1]
                          } # EXTENSION
        self.subtracted_names = []
        self.roughfrequencyrange = [1, 21]  # 粗略扫频的频率范围, 要看看SRF在什么地方，如果比较小的话感觉不太需要扫描两次
        self.PCBspace = 6 # mm
        self.res_path = kwargs["res_path"]
        self.report_files = []	# 保存文件夹名字
        self.ansys_handles = ansys_handles # ansys_handles := (oDesktop, oProject, oDesign, oEditor)
        self.compute_rad()
    
    def compute_rad(self):  # 
        w = self.kwargs["w"]
        # 初始化内径和外径
        self.radins = [self.kwargs["rout"] - w[0]]  # 第一个元素为 w1，用它计算初始内径
        self.radouts = [self.kwargs["rout"]]        # 初始化外径

        # 遍历 w 列表，跳过第一个元素
        for i in range(1, len(w)):
            current_w = w[i]          # 当前层的厚度
            previous_w = w[i - 1]     # 上一层的厚度

            # 计算新的内径和外径
            radin = self.radins[-1] - self.kwargs["space"] - current_w
            radout = self.radouts[-1] - self.kwargs["space"] - previous_w

            # 添加到列表中
            self.radins.append(radin)
            self.radouts.append(radout)
    
    # 在材料库中创建材料PTFE
    def create_PTFE(self):
        oProject = self.ansys_handles[-3]
        oDefinitionManager = oProject.GetDefinitionManager()
        oDefinitionManager.AddMaterial(
            [
                "NAME:PTFE",
                "CoordinateSystemType:=", "Cartesian",
                "BulkOrSurfaceType:="	, 1,
                [
                    "NAME:PhysicsTypes",
                    "set:="			, ["Electromagnetic","Thermal","Structural"]
                ],
                [
                    "NAME:AttachedData",
                    [
                        "NAME:MatAppearanceData",
                        "property_data:="	, "appearance_data",
                        "Red:="			, 27,
                        "Green:="		, 110,
                        "Blue:="		, 76
                    ]
                ],
                "permittivity:="	, "2.94",
                "dielectric_loss_tangent:=", "0.00016",
                "thermal_conductivity:=", "0.294",
                "mass_density:="	, "2270",
                "specific_heat:="	, "1150",
                "youngs_modulus:="	, "11000000000",
                "poissons_ratio:="	, "0.28",
                "thermal_expansion_coefficient:=", "1.5e-05"
            ])
        
    def create_PCB(self):   # PCB尺寸固定
        oEditor = self.ansys_handles[-1]
        
        RegularPolyhedron_name = oEditor.CreateRegularPolyhedron(
            [
                "NAME:PolyhedronParameters",
                "XCenter:="		, "0mm",
                "YCenter:="		, "0mm",
                "ZCenter:="		, "0mm",
                "XStart:="		, "0mm",
                "YStart:="		, "105mm",	# EXTENSION
                "ZStart:="		, "0mm",
                "Height:="		, "-1.52mm",
                "NumSides:="		, "36",
                "WhichAxis:="		, "Z"
            ], 
            [
                "NAME:Attributes",
                "Name:="		, "RegularPolyhedron1",
                "Flags:="		, "",
                "Color:="		, "(143 175 143)",
                "Transparency:="	, 0,
                "PartCoordinateSystem:=", "Global",
                "UDMId:="		, "",
                "MaterialValue:="	, "\"PTFE\"",
                "SurfaceMaterialValue:=", "\"\"",
                "SolveInside:="		, True,
                "ShellElement:="	, False,
                "ShellElementThickness:=", "0mm",
                "ReferenceTemperature:=", "20cel",
                "IsMaterialEditable:="	, True,
                "UseMaterialAppearance:=", False,
                "IsLightweight:="	, False
            ])
        self.obj_names["RegularPolyhedron"][0]["Board"].append(RegularPolyhedron_name)
        self.obj_names["RegularPolyhedron"][1] += 1
        
    def create_coils(self):
        radins, radouts = self.radins, self.radouts
        # radins, radouts = sorted(radins), sorted(radouts)
        n = self.kwargs["n"]
        oEditor = self.ansys_handles[-1]
        for i in range(1, 2 * n + 1):
            polygon_name = f"Polygon{i}"
            index = (i - 1) // 2  # 计算当前的索引，每两次循环后索引增加 1
            if i % 2 == 1:  # 如果 i 是奇数
                radius = radouts[index]
            else:  # 如果 i 是偶数
                radius = radins[index]
            oEditor.CreateRegularPolygon(  
                [
                    "NAME:RegularPolygonParameters",
                    "IsCovered:="		, True,
                    "XCenter:="		, "0mm",
                    "YCenter:="		, "0mm",
                    "ZCenter:="		, "0mm",
                    "XStart:="		, "0mm",
                    "YStart:="		, f"{radius}mm",  #EXTENSION
                    "ZStart:="		, "0mm",
                    "NumSides:="		, "58",
                    "WhichAxis:="		, "Z"
                ], 
                [
                    "NAME:Attributes",
                    "Name:="		, polygon_name,   
                    "Flags:="		, "",
                    "Color:="		, "(143 175 143)",
                    "Transparency:="	, 0,
                    "PartCoordinateSystem:=", "Global",
                    "UDMId:="		, "",
                    "MaterialValue:="	, "\"vacuum\"",
                        "SurfaceMaterialValue:=", "\"\"",
                    "SolveInside:="		, True,
                    "ShellElement:="	, False,
                    "ShellElementThickness:=", "0mm",
                    "ReferenceTemperature:=", "20cel",
                    "IsMaterialEditable:="	, True,
                    "UseMaterialAppearance:=", False,
                    "IsLightweight:="	, False
                ])
            self.obj_names["Polygon"][0]["Coil"].append(polygon_name)
            self.obj_names["Polygon"][1] += 1   # 每新建一个多边形，这个值就+1，创建了Polygon1对应这个值是2

            if i % 2 == 0:  # 如果i是偶数，就Polygon{i-1}-Polygon{i}
                oEditor.Subtract(
                    [
                        "NAME:Selections",
                        "Blank Parts:="		, f"Polygon{self.obj_names['Polygon'][1]-2}",
                        "Tool Parts:="		, f"Polygon{self.obj_names['Polygon'][1]-1}"
                    ], 
                    [
                        "NAME:SubtractParameters",
                        "KeepOriginals:="	, False,
                        "TurnOnNBodyBoolean:="	, True
                    ])
                self.subtracted_names.append(f"Polygon{self.obj_names['Polygon'][1]-1}")    # 记录被减去的部分的名字
    
    def create_gap(self):   # 减去线圈的一部分以链接内圈和外圈
        rout, oEditor = self.kwargs["rout"], self.ansys_handles[-1]
        rectangle_name = oEditor.CreateRectangle(
            [
            "NAME:RectangleParameters",
            "IsCovered:="		, True,
            "XStart:="		, "0mm", 
            "YStart:="		, "-4mm",   # fixed
            "ZStart:="		, "0mm",
            "Width:="		, f"-{rout+10}mm",  #EXTENSION
            "Height:="		, "8mm",    # fixed
            "WhichAxis:="		, "Z"
            ], 
            [
            "NAME:Attributes",
            "Name:="		, "Rectangle1",
            "Flags:="		, "",
            "Color:="		, "(143 175 143)",
            "Transparency:="	, 0,
            "PartCoordinateSystem:=", "Global",
            "UDMId:="		, "",
            "MaterialValue:="	, "\"vacuum\"",
            "SurfaceMaterialValue:=", "\"\"",
            "SolveInside:="		, True,
            "ShellElement:="	, False,
            "ShellElementThickness:=", "0mm",
            "ReferenceTemperature:=", "20cel",
            "IsMaterialEditable:="	, True,
            "UseMaterialAppearance:=", False,
            "IsLightweight:="	, False
            ])
        self.obj_names["Rectangle"][0]["Gap"].append(rectangle_name)
        self.obj_names["Rectangle"][1] += 1
        
        oEditor.Subtract(
            [
                "NAME:Selections",
                "Blank Parts:="		, ",".join([part for part in self.obj_names['Polygon'][0]["Coil"] if part not in self.subtracted_names]),   #得用“A,B,C"的格式
                "Tool Parts:="		, "Rectangle1"
            ], 
            [
                "NAME:SubtractParameters",
                "KeepOriginals:="	, False,
                "TurnOnNBodyBoolean:="	, True
            ])
        self.subtracted_names.append(rectangle_name)
        
    def create_polylines(self):
        radins, radouts = self.radins, self.radouts
        oEditor = self.ansys_handles[-1]
        # x = 4 / np.tan(np.radians(46/48*180 / 2))  #  两边夹角theta = (n-2)/n * 180
        # x = 4 / np.tan(np.radians(38/40*180 / 2))  #  58边形
        
        for i in range(len(radins)-1):
            polyline_name = oEditor.CreatePolyline(
                [
                    "NAME:PolylineParameters",
                    "IsPolylineCovered:="	, True,
                    "IsPolylineClosed:="	, True,
                    [
                        "NAME:PolylinePoints",
                        [
                            "NAME:PLPoint",
                            # "X:="			, f"-{radins[i+1]-x}mm",
                            "X:="			, f"-{np.sqrt(radins[i+1]**2-16)}mm",	    
                            "Y:="			, "-4mm",
                            "Z:="			, "0mm"
                        ],
                        [
                            "NAME:PLPoint",
                            # "X:="			, f"-{radins[i]-x}mm",  
                            "X:="			, f"-{np.sqrt(radins[i]**2-16)}mm",  
                            "Y:="			, "4mm",
                            "Z:="			, "0mm"
                        ],
                        [
                            "NAME:PLPoint",
                            # "X:="			, f"-{radouts[i]-x}mm",     
                            "X:="			, f"-{np.sqrt(radouts[i]**2-16)}mm",  
                            "Y:="			, "4mm",
                            "Z:="			, "0mm"
                        ],
                        [
                            "NAME:PLPoint",
                            # "X:="			, f"-{radouts[i+1]-x}mm",    
                            "X:="			, f"-{np.sqrt(radouts[i+1]**2-16)}mm",  
                            "Y:="			, "-4mm",
                            "Z:="			, "0mm"
                        ],
                        [
                            "NAME:PLPoint",
                            # "X:="			, f"-{radins[i+1]-x}mm",     
                            "X:="			, f"-{np.sqrt(radins[i+1]**2-16)}mm",  
                            "Y:="			, "-4mm",
                            "Z:="			, "0mm"
                        ]
                    ],
                    [
                        "NAME:PolylineSegments",
                        [
                            "NAME:PLSegment",
                            "SegmentType:="		, "Line",
                            "StartIndex:="		, 0,
                            "NoOfPoints:="		, 2
                        ],
                        [
                            "NAME:PLSegment",
                            "SegmentType:="		, "Line",
                            "StartIndex:="		, 1,
                            "NoOfPoints:="		, 2
                        ],
                        [
                            "NAME:PLSegment",
                            "SegmentType:="		, "Line",
                            "StartIndex:="		, 2,
                            "NoOfPoints:="		, 2
                        ],
                        [
                            "NAME:PLSegment",
                            "SegmentType:="		, "Line",
                            "StartIndex:="		, 3,
                            "NoOfPoints:="		, 2
                        ]
                    ],
                    [
                        "NAME:PolylineXSection",
                        "XSectionType:="	, "None",
                        "XSectionOrient:="	, "Auto",
                        "XSectionWidth:="	, "0mm",
                        "XSectionTopWidth:="	, "0mm",
                        "XSectionHeight:="	, "0mm",
                        "XSectionNumSegments:="	, "0",
                        "XSectionBendType:="	, "Corner"
                    ]
                ], 
                [
                    "NAME:Attributes",
                    "Name:="		, f"Polyline{self.obj_names['Polyline'][1]}",      # 每生成一个之后会+1，初始是1
                    "Flags:="		, "",
                    "Color:="		, "(143 175 143)",
                    "Transparency:="	, 0,
                    "PartCoordinateSystem:=", "Global",
                    "UDMId:="		, "",
                    "MaterialValue:="	, "\"vacuum\"",
                    "SurfaceMaterialValue:=", "\"\"",
                    "SolveInside:="		, True,
                    "ShellElement:="	, False,
                    "ShellElementThickness:=", "0mm",
                    "ReferenceTemperature:=", "20cel",
                    "IsMaterialEditable:="	, True,
                    "UseMaterialAppearance:=", False,
                    "IsLightweight:="	, False
                ])
            self.obj_names["Polyline"][0]["Connector"].append(polyline_name)
            self.obj_names["Polyline"][1] += 1	# 修改命名
    
    def create_second_PCB(self): 
        oDesign = self.ansys_handles[-2]
        filtered_coil_elements = [elem for elem in self.obj_names["Polygon"][0]["Coil"] if elem not in self.subtracted_names]
        oEditor = oDesign.SetActiveEditor("3D Modeler")
        first_pcb = ",".join(self.obj_names["RegularPolyhedron"][0]["Board"]
                            + filtered_coil_elements
                            + self.obj_names["Polyline"][0]["Connector"])
        second_pcb = oEditor.DuplicateAroundAxis(
            [
                "NAME:Selections",
                "Selections:="		, first_pcb,
                "NewPartsModelFlag:="	, "Model"
            ], 
            [
                "NAME:DuplicateAroundAxisParameters",
                "CreateNewObjects:="	, True,
                "WhichAxis:="		, "X",
                "AngleStr:="		, "180deg",
                "NumClones:="		, "2"
            ], 
            [
                "NAME:Options",
                "DuplicateAssignments:=", True
            ], 
            [
                "CreateGroupsForNewObjects:=", False
            ])
        
        self.obj_names["SecondPCB"][0]["Second"] = second_pcb

        oEditor.Move(
            [
                "NAME:Selections",
                "Selections:="		, ",".join(second_pcb),
                "NewPartsModelFlag:="	, "Model"
            ], 
            [
                "NAME:TranslateParameters",
                "TranslateVectorX:="	, "0mm",
                "TranslateVectorY:="	, "0mm",
                "TranslateVectorZ:="	, f"{self.PCBspace}mm"    # EXTENSION
            ])

    def create_leads(self): 
        oEditor = self.ansys_handles[-1]
        radins, radouts = self.radins, self.radouts
        lead_width = 1.5  # 导线宽度1mm
        w_innermost = self.kwargs["w"][-1]
        # x = 4 / np.tan(np.radians(165 / 2))  # 常数
        # x = 4 / np.tan(np.radians(46/48*180 / 2))  
        lead_x = 20     # 20mm
        # XPositions = [-(radins[0] - x), -(radins[0] - x)- lead_x, -(radins[0] - x), -(radins[0] - x)- lead_x + lead_width]
        XPositions = [-np.sqrt(radins[0]**2 - 16), -np.sqrt(radins[0]**2 - 16)- lead_x, -np.sqrt(radins[0]**2 - 16), -np.sqrt(radins[0]**2 - 16)- lead_x + lead_width]
        YPositions = [4, 4-lead_width, -4, -(4-lead_width)]
        ZPositions = [self.PCBspace , self.PCBspace , 0, 0]
        Widths =     [-lead_x, -self.PCBspace, -lead_x, -lead_width]
        Heights =    [-lead_width, lead_width, lead_width, 8 - 2 * lead_width]
        WhichAxiss = ["Z", "Y", "Z", "Z"]
        
        for i,(XPosition, YPosition, ZPosition, Width, Height, WhichAxis) in enumerate(zip(XPositions, YPositions, 
                                                                                ZPositions, Widths, 
                                                                                Heights, WhichAxiss)):
            retcangle_name = oEditor.CreateRectangle(
                [
                    "NAME:RectangleParameters",
                    "IsCovered:="		, True,
                    "XStart:="		, f"{XPosition}mm",
                    "YStart:="		, f"{YPosition}mm",
                    "ZStart:="		, f"{ZPosition}mm",
                    "Width:="		, f"{Width}mm",         
                    "Height:="		, f"{Height}mm",        
                    "WhichAxis:="	, WhichAxis
                ], 
                [
                    "NAME:Attributes",
                    "Name:="		, f"Rectangle{self.obj_names['Exitation'][1]}", # EXITATION
                    "Flags:="		, "",
                    "Color:="		, "(143 175 143)",
                    "Transparency:="	, 0,
                    "PartCoordinateSystem:=", "Global",
                    "UDMId:="		, "",
                    "MaterialValue:="	, "\"vacuum\"",
                    "SurfaceMaterialValue:=", "\"\"",
                    "SolveInside:="		, True,
                    "ShellElement:="	, False,
                    "ShellElementThickness:=", "0mm",
                    "ReferenceTemperature:=", "20cel",
                    "IsMaterialEditable:="	, True,
                    "UseMaterialAppearance:=", False,
                    "IsLightweight:="	, False
                ])
            self.obj_names["Exitation"][0]["Exitation"].append(retcangle_name)  # Rectangle5是exitation，其他是理想导体
            self.obj_names["Exitation"][1] += 1    
    
    def assign_boundary(self):
        oDesign, oEditor = self.ansys_handles[-2], self.ansys_handles[-1]
        
        # 使用列表推导式排除Rectangle5，Rectangle5是exitation
        boundary = [rect for rect in self.obj_names["Exitation"][0]["Exitation"] if rect != "Rectangle5"]
        filtered_coil_elements = [elem for elem in self.obj_names["Polygon"][0]["Coil"] if elem not in self.subtracted_names]
        all_objects = boundary + filtered_coil_elements + self.obj_names["Polyline"][0]["Connector"] + self.obj_names["SecondPCB"][0]["Second"][1:]
        
        # 设置有限导体边界，设置为铜
        oModule = oDesign.GetModule("BoundarySetup")
        oModule.AssignFiniteCond( # 已修改
            [
                "NAME:FiniteCond1",
                "Objects:="		    , all_objects,
                "UseMaterial:="		, True,
                "Material:="		, "copper",
                "UseThickness:="	, False,
                "Roughness:="		, "0um",
                "InfGroundPlane:="	, False,
                "IsTwoSided:="		, False,
                "IsInternal:="		, True
            ])
        
        # 设置terminal lumped port
        oModule.AutoIdentifyPorts(
            [
                "NAME:Faces", 
                int(oEditor.GetFaceIDs("Rectangle5")[0])
            ], False, 
            [
                "NAME:ReferenceConductors", 
                "Rectangle3"
            ], "1", True)
        
        # 绘制空气盒子，尺寸注意600*600*600mm
        oEditor.CreateRegion(
            [
                "NAME:RegionParameters",
                "+XPaddingType:="	, "Absolute Position",
                "+XPadding:="		, "300mm",
                "-XPaddingType:="	, "Absolute Position",
                "-XPadding:="		, "-300mm",
                "+YPaddingType:="	, "Absolute Position",
                "+YPadding:="		, "300mm",
                "-YPaddingType:="	, "Absolute Position",
                "-YPadding:="		, "-300mm",
                "+ZPaddingType:="	, "Absolute Position",
                "+ZPadding:="		, "300mm",
                "-ZPaddingType:="	, "Absolute Position",
                "-ZPadding:="		, "-300mm",
                [
                    "NAME:BoxForVirtualObjects",
                    [
                        "NAME:LowPoint", 
                        1, 
                        1, 
                        1
                    ],
                    [
                        "NAME:HighPoint", 
                        -1, 
                        -1, 
                        -1
                    ]
                ]
            ], 
            [
                "NAME:Attributes",
                "Name:="		, "Region",
                "Flags:="		, "Wireframe#",
                "Color:="		, "(143 175 143)",
                "Transparency:="	, 0,
                "PartCoordinateSystem:=", "Global",
                "UDMId:="		, "",
                "MaterialValue:="	, "\"vacuum\"",
                "SurfaceMaterialValue:=", "\"\"",
                "SolveInside:="		, True,
                "ShellElement:="	, False,
                "ShellElementThickness:=", "nan ",
                "ReferenceTemperature:=", "nan ",
                "IsMaterialEditable:="	, True,
                "UseMaterialAppearance:=", False,
                "IsLightweight:="	, False
            ])
    
    def assign_mesh(self):  # 在精确扫描阶段前设定mesh
        oDesign = self.ansys_handles[-2]
        oModule = oDesign.GetModule("MeshSetup")
        filtered_coil_elements = [elem for elem in self.obj_names["Polygon"][0]["Coil"] if elem not in self.subtracted_names]
        all_objects = self.obj_names["Exitation"][0]["Exitation"] + filtered_coil_elements + self.obj_names["Polyline"][0]["Connector"] + self.obj_names["SecondPCB"][0]["Second"] + ["RegularPolyhedron1"]


        oModule.AssignLengthOp(
            [
                "NAME:Length1",
                "RefineInside:="	, False,
                "Enabled:="		    , True,
                "Objects:="		    , all_objects,
                "RestrictElem:="	, False,
                "NumMaxElem:="		, "1000",
                "RestrictLength:="	, True,
                "MaxLength:="		, "6mm"
            ])
        
    def analysis_setup(self, stage_idx=0):
        oDesign = self.ansys_handles[-2]
        oModule = oDesign.GetModule("AnalysisSetup")
        if stage_idx == 0:
            oModule.InsertSetup("HfssDriven", 
                [
                    "NAME:Setup1",
                    "SolveType:="		, "Broadband",
                    [
                        "NAME:MultipleAdaptiveFreqsSetup",
                        "Low:="			, f"{self.roughfrequencyrange[0]}MHz",	# EXTENSION
                        "High:="		, f"{self.roughfrequencyrange[1]}MHz"	# EXTENSION
                    ],
                    "MaxDeltaS:="		, 0.02,
                    "MaximumPasses:="	, 6,
                    "MinimumPasses:="	, 1,
                    "MinimumConvergedPasses:=", 1,
                    "PercentRefinement:="	, 30,
                    "IsEnabled:="		, True,
                    [
                        "NAME:MeshLink",
                        "ImportMesh:="		, False
                    ],
                    "BasisOrder:="		, 1,
                    "DoLambdaRefine:="	, True,
                    "DoMaterialLambda:="	, True,
                    "SetLambdaTarget:="	, True,
                    "Target:="		, 0.4,
                    "UseMaxTetIncrease:="	, False,
                    "PortAccuracy:="	, 2,
                    "UseABCOnPort:="	, False,
                    "SetPortMinMaxTri:="	, False,
                    "DrivenSolverType:="	, "Direct Solver",
                    "EnhancedLowFreqAccuracy:=", False,
                    "SaveRadFieldsOnly:="	, False,
                    "SaveAnyFields:="	, False,
                    "IESolverType:="	, "Auto",
                    "LambdaTargetForIESolver:=", 0.15,
                    "UseDefaultLambdaTgtForIESolver:=", True,
                    "IE Solver Accuracy:="	, "Balanced",
                    "InfiniteSphereSetup:="	, ""
                ])
        # Create frequency setup
        # 根据识别的阶段来区分是粗扫描还是精细扫描
        if stage_idx == 0:
            # If stage_idx == 0: rough search
            range_start = self.roughfrequencyrange[0] # EXTENSION
            range_end = self.roughfrequencyrange[1] # EXTENSION
            range_count = 201 # EXTENSION
            method = oModule.InsertFrequencySweep
            params = ("Setup1", )
        elif stage_idx == 1:
            # If stage_idx == 0: detailed search
            range_start = self.range_start2
            range_end = self.range_end2
            range_count = 501 
            method = oModule.EditFrequencySweep
            params = ("Setup1", "Sweep")
        method(*params, 
       	[
            "NAME:Sweep",
            "IsEnabled:="		, True,
            "RangeType:="		, "LinearCount",
            "RangeStart:="		, f"{range_start}MHz",	
            "RangeEnd:="		, f"{range_end}MHz",	
            "RangeCount:="		, range_count,		
            "Type:="		    , "Interpolating",
            "SaveFields:="		, False,
            "SaveRadFields:="	, False,
            "InterpTolerance:="	, 0.5,
            "InterpMaxSolns:="	, 250,
            "InterpMinSolns:="	, 0,
            "InterpMinSubranges:="	, 1,
            "InterpUseS:="		, True,
            "InterpUsePortImped:="	, True,
            "InterpUsePropConst:="	, True,
            "UseDerivativeConvergence:=", False,
            "InterpDerivTolerance:=", 0.2,
            "UseFullBasis:="	, True,
            "EnforcePassivity:="	, True,
            "PassivityErrorTolerance:=", 0.0001,
            "EnforceCausality:="	, False,
            "SMatrixOnlySolveMode:=", "Auto"
       	])
        
    def save_results(self, stage_idx=0):
        # =============================================================================
        #     Save results
        # =============================================================================
        oProject, oDesign = self.ansys_handles[1:3]
        # 保存ZLR三个曲线
        report = f"index{self.index}-dB20Z"
        report_file = f"{report}-Stage{stage_idx}.csv"
        self.report_files.append(self.res_path+"/"+report_file)
        # Define the Reports to be created
        if stage_idx == 0:
            oModule = oDesign.GetModule("ReportSetup")
            oModule.CreateReport(report, "Terminal Solution Data", "Rectangular Plot", "Setup1 : Sweep", 	# dB20Z
                [
                    "Domain:="		, "Sweep"
                ], 
                [
                    "Freq:="		, ["All"]
                ], 
                [
                    "X Component:="		, "Freq",
                    "Y Component:="		, ["dB20(Zt(Rectangle4_T1,Rectangle4_T1))"]         # 要注意
                ])
        # Save project
        oProject.Save()
        # oDesign.AnalyzeAll()
        # Start analysis
        oDesign.Analyze("Setup1 : Sweep")
        oModule = oDesign.GetModule("ReportSetup") 
        # Expot results
        oModule.ExportToFile(report, self.report_files[-1], False)   
    
    # 每完成一个就关闭掉
    def close_design(self):
        oProject = self.ansys_handles[1]
        oProject.Close()
        
    def run(self):
        self.create_PTFE()
        
        self.create_PCB()
        
        self.create_coils()
        
        self.create_gap()
        
        self.create_polylines()

        self.create_second_PCB()
        
        self.create_leads()
        
        self.assign_boundary()
        
        self.assign_mesh()
        # Two-stage analysis
        # 1st stage: locate the rough region of self-resonant frequency (SRF) point
        # 2nd stage: search the located SRF region
        # 两阶段分析

        for stage_idx in range(2):    # 串联谐振
            # if stage_idx == 1:
            #     self.assign_mesh()
            self.analysis_setup(stage_idx)
            self.save_results(stage_idx)
            if stage_idx == 0:
                # locate the rough region
                dB20Z_data = np.loadtxt(self.report_files[0], delimiter=",", skiprows=1)	# 读取文件数据
                min_indices = argrelextrema(dB20Z_data[:, 1], np.less)[0]
                if len(min_indices) > 0:
                    first_valley_idx = min_indices[0]
                else:
                    raise AssertionError("Not able to find the SRF.")
                # 检查最小值是否位于数据的边缘。如果最大值位于第一个或最后一个数据点，表示未能找到合适的谐振频率
                if (first_valley_idx == 0) or (first_valley_idx == dB20Z_data.shape[0]-1):
                    raise AssertionError("Not able to find the SRF")

                self.range_start2 = dB20Z_data[first_valley_idx-5, 0]	# EXTENSION
                self.range_end2 = dB20Z_data[first_valley_idx+5, 0]		 

    def run_dict_search(self, SRF_ref=3.03):
        self.create_PTFE()
        
        self.create_PCB()
        
        self.create_coils()

        self.create_gap()

        self.create_polylines()

        self.create_second_PCB()
        
        self.create_leads()
        
        self.assign_boundary()        
        # self.assign_mesh()
        for stage_idx in range(2):   
            freq_diff = 0   # 初始化为0
            if stage_idx == 1:
                self.assign_mesh()
            self.analysis_setup(stage_idx)
            self.save_results(stage_idx)
            if stage_idx == 0:
                dB20Z_data = np.loadtxt(self.report_files[0], delimiter=",", skiprows=1)	
                min_indices = argrelextrema(dB20Z_data[:, 1], np.less)[0]
                if len(min_indices) > 0:
                    first_valley_idx = min_indices[0]
                else:
                    raise AssertionError("Not able to find the SRF.")
                # 检查最小值是否位于数据的边缘。如果最大值位于第一个或最后一个数据点，表示未能找到合适的谐振频率
                if (first_valley_idx == 0) or (first_valley_idx == dB20Z_data.shape[0]-1):
                    raise AssertionError("Not able to find the SRF")
                # 如果串联谐振点偏离目标频率>0.1MHz则不进入下一阶段
                if np.abs(dB20Z_data[first_valley_idx, 0] - SRF_ref) > 0.1:
                    raise AssertionError("The series resonance point deviates from the target frequency by 0.1MHz.")

                # 找到波峰——并联谐振点
                max_indices = argrelextrema(dB20Z_data[:, 1], np.greater)[0]
                if len(max_indices) > 0:
                    first_peak_idx = max_indices[0]
                    freq_diff=np.abs(dB20Z_data[first_peak_idx, 0] - dB20Z_data[first_valley_idx, 0])
                # 如果两个谐振频率之间的差距小于2.2MHz，则不进入下一阶段。如果没有找到波峰，则直接进入下一阶段
                if 0 < freq_diff < 1.95:
                    raise AssertionError("The difference between SRF1 and SRF2 less than 1.95MHz.")

                self.range_start2 = dB20Z_data[first_valley_idx-5, 0]   # EXTENSION
                self.range_end2 = dB20Z_data[first_valley_idx+5, 0]	
    
    def parse_results(self):
        dB20Z_data = np.loadtxt(self.report_files[1], delimiter=",", skiprows=1)   # 0是粗略阶段，1是精细阶段
        dB20Z_data0 = np.loadtxt(self.report_files[0], delimiter=",", skiprows=1)
        # 串联谐振
        min_indices = argrelextrema(dB20Z_data[:, 1], np.less)[0]
        if len(min_indices) > 0:
            first_valley_idx = min_indices[0]
            SRF1 = dB20Z_data[first_valley_idx, 0]
        else:
            first_valley_idx = np.argmin(dB20Z_data[:, 1])  
            SRF1 = dB20Z_data[first_valley_idx, 0]

        # 并联谐振
        max_indices = argrelextrema(dB20Z_data0[:, 1], np.greater)[0]
        if len(max_indices) > 0:
            first_peak_idx = max_indices[0]
            SRF2 = dB20Z_data0[first_peak_idx, 0]
        else:
            SRF2 = 0
        Z_RF = dB20Z_data[first_valley_idx, 1]
        tmp = Z_RF+3
        idx_3db_left_candidates = np.where((dB20Z_data[:-1, 1] > tmp) & (dB20Z_data[1:, 1] < tmp))[0]     # 大于变成小于
        idx_3db_right_candidates = np.where((dB20Z_data[:-1, 1] < tmp) & (dB20Z_data[1:, 1] > tmp))[0]    # 小于变成大于        
        if len(idx_3db_left_candidates) > 0 and len(idx_3db_right_candidates) > 0:
            idx_3db_left = idx_3db_left_candidates[0]
            idx_3db_right = idx_3db_right_candidates[0] + 1
            xp = dB20Z_data[idx_3db_left:idx_3db_right+1, 0]
            x = np.arange(xp[0], xp[-1]+(xp[-1]-xp[0])/1000, (xp[-1]-xp[0])/1000)
            y_interp = np.interp(x, xp, dB20Z_data[idx_3db_left:idx_3db_right+1, 1])
            idx_3db_left = np.where((y_interp[:-1]>tmp)&(y_interp[1:]<tmp))[0][0]                   # 大于变成小于
            idx_3db_right = np.where((y_interp[:-1]<tmp)&(y_interp[1:]>tmp))[0][0]+1                # 小于变成大于

            Q_small = x[idx_3db_left]
            Q_big = x[idx_3db_right]
            e = abs(Q_big-Q_small)
            Q = dB20Z_data[first_valley_idx, 0]/e
        else:
            SRF1 = 0
            Q = 0

        self.parsed_results = {"SRF1": SRF1, "SRF2": SRF2, "Q": Q}
        return self.parsed_results

def init_ansys(oDesktop):
    # import ScriptEnv
    # ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
    hfss_app = Hfss(projectname=None, designname="HFSSDesign1", solution_type="DrivenTerminal", specified_version="2023.1")
    oDesktop = hfss_app.odesktop
    oDesktop.RestoreWindow()
    oProject = hfss_app.oproject
    # oProject = oDesktop.SetActiveProject(f"Project{project_idx}")
    # oProject.InsertDesign("HFSS", f"HFSSDesign{HFSSd_idx}", "DrivenModal", "")
    oDesign = hfss_app.odesign
    oDesign.SetSolutionType("DrivenTerminal", 
        [
            "NAME:Options",
            "EnableAutoOpen:=", False
        ])
    oEditor = oDesign.SetActiveEditor("3D Modeler")
    return oDesktop, oProject, oDesign, oEditor

def run(config_file, desktop_instance=None, index=None):
    start_time = time.time()
    try:
        # 读取配置文件
        with open(config_file, "r+") as f:
            kwargs = json.load(f)
        
        # 初始化 AEDT Desktop 实例
        if desktop_instance is None:
            desktop_instance = Desktop(
                specified_version=f"{kwargs['Ansys_version']}",
                non_graphical=False,
                close_on_exit=False,    # 如果想把ansys关掉的话就设置为True
                student_version=False
            )
        
        # 初始化 Ansys 环境并解包返回值
        oDesktop, oProject, oDesign, oEditor = init_ansys(desktop_instance.odesktop)
        
        # 检查 project_list 是否为空，防止 list index out of range 错误
        project_list = desktop_instance.project_list()
        if project_list:
            kwargs["project_id"] = project_list[-1]
        else:
            raise ValueError("No project found in the desktop instance.")
        
        # 记录项目路径
        kwargs["project_path"] = desktop_instance.project_path()
        
        # 更新配置文件
        with open(config_file, "w+") as f:
            json.dump(kwargs, f)
        
        # 打印调试信息，确保 Ansys handles 正确
        # print(f"Ansys handles: oDesktop={oDesktop}, oProject={oProject}, oDesign={oDesign}, oEditor={oEditor}")
        
        # 创建 IPTCoil 对象
        ansys_handles = (oDesktop, oProject, oDesign, oEditor)
        cir_pcb = IPTCoil(kwargs, ansys_handles, index=index)
        
        # 运行 cir_pcb
        cir_pcb.run()   
        if_success = True
        cir_pcb.parsed_results = cir_pcb.parse_results() # EXTENSION
    
    except Exception as e:
        # 捕获异常，确保 cir_pcb 存在才赋值错误日志
        print(f"An error occurred: {e}")
        if 'cir_pcb' in locals():
            cir_pcb.error_log = e
        if_success = False
        
    # cir_pcb.close_design()
    # desktop_instance.release_desktop(close_projects=True)


    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"仿真时间为:{elapsed_time:.4f}秒")

    # 返回 cir_pcb 和 if_success 状态
    return cir_pcb, if_success

def run_dict_search(config_file, desktop_instance=None, index=None, SRF_ref=3.03):
    start_time = time.time()
    try:
        with open(config_file, "r+") as f:
            kwargs = json.load(f)
        
        if desktop_instance is None:
            desktop_instance = Desktop(
                specified_version=f"{kwargs['Ansys_version']}",
                non_graphical=False,
                close_on_exit=False,    # 如果想把ansys关掉的话就设置为True
                student_version=False
            )
        
        oDesktop, oProject, oDesign, oEditor = init_ansys(desktop_instance.odesktop)
        
        project_list = desktop_instance.project_list()
        if project_list:
            kwargs["project_id"] = project_list[-1]
        else:
            raise ValueError("No project found in the desktop instance.")

        kwargs["project_path"] = desktop_instance.project_path()

        with open(config_file, "w+") as f:
            json.dump(kwargs, f)

        ansys_handles = (oDesktop, oProject, oDesign, oEditor)
        cir_pcb = IPTCoil(kwargs, ansys_handles, index=index)
        
        cir_pcb.run_dict_search(SRF_ref=SRF_ref)   
        if_success = True
        cir_pcb.parsed_results = cir_pcb.parse_results() 
    
    except Exception as e:
        print(f"An error occurred: {e}")
        if 'cir_pcb' in locals():
            cir_pcb.error_log = e
        if_success = False
        
    cir_pcb.close_design()
    # desktop_instance.release_desktop(close_projects=True)

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"仿真时间为:{elapsed_time:.4f}秒")

    return cir_pcb, if_success
