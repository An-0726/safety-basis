# 接手说明

- 长期工作边界：[AGENTS.md](../AGENTS.md)。
- 阶段、已核事实、暂停状态和恢复计划：[PROJECT_STATE](PROJECT_STATE.md)。该文件标注核验日期，不代表每次读取时重新验证。
- 架构与维护说明：[README](../README.md)。
- 确需跨环境协作：[执行协议](../AGENT_EXECUTION_PROTOCOL.md)。

先理解本次用户目标；只有用户要求接续业务阶段时才采用恢复计划。当前规则重构没有恢复PHASE 5交付或PHASE 6候选核验，也没有改变正式数据。

阶段事实只维护一份，不在HANDOFF复制库存数字或长期待办。低风险局部任务完成相关检查后即可结束。
