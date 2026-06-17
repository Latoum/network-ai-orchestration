# BGP EVPN / VXLAN Spine-Leaf Fabric

A VXLAN fabric uses a spine-leaf (Clos) topology where every leaf connects to every spine.
VXLAN provides Layer 2 overlay tunnels across a routed Layer 3 underlay, identified by a
24-bit VNI (VXLAN Network Identifier) that scales to ~16 million segments, far beyond the
4,094-segment limit of traditional 802.1Q VLANs.

MP-BGP EVPN is the control plane for VXLAN. Instead of flood-and-learn, leaf switches act as
VTEPs (VXLAN Tunnel Endpoints) and advertise MAC and IP reachability as EVPN Type-2 routes,
and prefix reachability as Type-5 routes. EVPN Type-3 routes handle multicast/ingress
replication for BUM (broadcast, unknown-unicast, multicast) traffic.

Design guidance: use an anycast gateway so the same distributed default gateway IP/MAC lives on
every leaf, enabling seamless workload mobility. Run the spine layer as BGP route reflectors to
avoid a full iBGP mesh. The underlay typically runs OSPF or eBGP for VTEP-to-VTEP reachability,
with the EVPN address family carried over BGP on top. Symmetric IRB (Integrated Routing and
Bridging) is preferred for east-west routing because it scales better than asymmetric IRB.

Common failure domains: an MTU mismatch breaks VXLAN encapsulation (the 50-byte VXLAN header
requires jumbo MTU on the underlay), and inconsistent route-target import/export policy causes
silent reachability loss between VRFs.
