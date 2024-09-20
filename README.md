# PyIKuaiMiddle

大概是 iKuai 路由系统的 WebUI 上的 API 的中间代理程序，主要是为了未来供我的 Bot 和 Uptime Kuma 使用，用以监测幽默校园网的在线情况 —— 换句话说就是自用的，并且多少也有点找乐子的成分在里面大概。

> `lemonyikuai` 模块的有些地方可能和 [`PyIKuaiClient`](https://github.com/dzhuang/PyIKuaiClient) 项目的实现很像，实际上我是写了一截之后发现有这个包，于是将它的登录实现搬了过来就懒得自己逆了。不过其余部分就是完全自己写的就是了，最终(?)的实现效果像是 `PyIKuaiClient` 的丐中丐中丐版本ww（毕竟只是为了做状态监控）
>
> 总之非常感谢 `PyIKuaiClient` 项目的作者w，快去给ta点小星星w
