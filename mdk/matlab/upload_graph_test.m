% MATLAB upload graph test for SysML DocGen.
% sysml-docgen:begin
% {
%   "elements": [
%     {
%       "id": "REQ-UPLOAD-MAT-001",
%       "name": "上传新增 MATLAB 图谱验证需求",
%       "type": "Requirement",
%       "stereotype": "requirement",
%       "description": "用于验证 MATLAB 脚本上传后新增元素能显示在 Graph 页签。",
%       "owner": "MDK验证组",
%       "attributes": {
%         "text": "系统应支持从 MATLAB 脚本标记导入新增需求。",
%         "verification": "Demo"
%       },
%       "relations": [
%         {"type": "satisfy", "target": "BLK-UPLOAD-MAT-001"},
%         {"type": "verify", "target": "TST-UPLOAD-MAT-001"}
%       ]
%     },
%     {
%       "id": "BLK-UPLOAD-MAT-001",
%       "name": "上传新增 MATLAB 图谱验证模块",
%       "type": "Block",
%       "stereotype": "block",
%       "relations": []
%     },
%     {
%       "id": "TST-UPLOAD-MAT-001",
%       "name": "上传新增 MATLAB 图谱验证用例",
%       "type": "TestCase",
%       "stereotype": "testCase",
%       "attributes": {
%         "method": "MATLAB Script Upload",
%         "criterion": "Graph shows MATLAB imported relations"
%       },
%       "relations": []
%     }
%   ]
% }
% sysml-docgen:end

disp("SysML DocGen upload graph test");
