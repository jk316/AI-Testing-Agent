我要实现输入自然语言测试意图，之后进行
→ 结构化语义（DSL）
→ 可执行网络流量（hping3）
→ 验证是否符合意图
本质是：一个“网络测试编译器 + 执行验证系统”。
如果需要代码，用python语言实现

架构：
[User Input]
      ↓
Planner Agent
(NL → DSL)
      ↓
Compiler Agent
(DSL → hping3)
      ↓
Verifier Agent
(语义校验)
      ↓
可执行脚本


### 1输入层（User Intent）
自然语言测试计划
特点：
模糊（低频、隐蔽）
Planner Agent 必须具备根据上下文推断缺省参数的能力（如未指定端口则默认 80）

### 2语义层（DSL）
{
  "protocol": "TCP",
  "rate": "low",
  "stealth": true,
  "target": "...",
  ...
}
作用：把“模糊语言”变成“可计算语义”

### 3编译层（Mapping / Compiler）
DSL → hping3 命令
依赖：
参数规则（来自 manpage）
约束系统（你定义）


### 4验证层（Verifier）
命令 → 是否符合测试意图？
检查：
速率是否符合
是否满足隐蔽
flag 是否正确
是否存在冲突等