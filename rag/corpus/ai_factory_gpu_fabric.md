# AI Factory GPU/Back-End Network Fabric

An "AI Factory" is a data-center design optimized for large-scale model training and inference.
Its defining feature is a dedicated, lossless back-end fabric that interconnects GPU servers,
separate from the front-end/management network.

GPU collective operations (all-reduce, all-gather) generate intense, synchronized east-west
traffic. A single straggling flow stalls the entire training job, so the back-end fabric is
engineered for predictable, low tail-latency rather than average throughput. Designs use rail-
optimized topologies where each GPU's NIC maps to a specific leaf ("rail") to minimize cross-
fabric hops.

Lossless transport is achieved with RoCEv2 (RDMA over Converged Ethernet) plus PFC (Priority
Flow Control) and ECN/DCQCN for congestion management; alternatively InfiniBand is used. NVIDIA-
certified Ethernet designs (e.g., Spectrum-X, or Cisco Nexus with the appropriate buffering and
telemetry) target the same goal: near-zero packet loss under bursty collective traffic.

Capacity planning: non-blocking or low-oversubscription Clos fabrics are typical, with 400G/800G
links between leaf and spine. Cabling, optics, and power density per rack are first-order design
constraints. Job scheduling and topology awareness (placing ranks of a job on the same rail/pod)
materially affect training throughput.
