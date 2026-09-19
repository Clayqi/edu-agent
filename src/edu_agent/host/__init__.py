"""edu_agent.host —— 进程级基础设施层（第一阶段：对照 DSH host 平面收口）。

host 平面只拥有"全进程唯一、跨 Agent 共享"的东西：
  - store.SessionStore  会话持久化（按 session_id 键控，替代 web_server 模块级全局 dict）
  - routing 不属于 host，但同属收口面：路由策略单一来源，见 edu_agent.routing

Agent 平面（coach=generate、planner、supervisor）保持各自独立入口不变，
host 层只提供它们和网关共同依赖的底座，不进入任何 Agent 的业务内部。
"""
