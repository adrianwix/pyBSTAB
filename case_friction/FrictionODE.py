import torch
from typing import TypedDict
from pybasin.ODESystem import ODESystem


class FrictionParams(TypedDict):
    """
    Parameters for the friction ODE system.
    Adjust them as needed to match your scenario.
    """
    v_d: float     # Driving velocity
    xi: float      # Damping ratio
    musd: float    # Ratio of static to dynamic friction coefficient
    mud: float     # Dynamic friction coefficient
    muv: float     # Linear strengthening parameter
    v0: float      # Reference velocity for exponential decay


class FrictionODE(ODESystem[FrictionParams]):
    """
    ODE System for a friction-based SDOF oscillator,
    adapted from ode_friction.m.
    """

    def __init__(self, params: FrictionParams):
        super().__init__(params)

    def ode(self, t: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        v_d = self.params["v_d"]
        xi = self.params["xi"]
        musd = self.params["musd"]
        mud = self.params["mud"]
        muv = self.params["muv"]
        v0 = self.params["v0"]

        disp = y[..., 0]
        vel = y[..., 1]

        vrel = vel - v_d
        eta = 1e-4
        k_smooth = 50  # Controls transition smoothness

        # Inlined friction force calculation
        Ffric = (mud
                 + mud * (musd - 1.0) * torch.exp(-torch.abs(vrel) / v0)
                 + muv * torch.abs(vrel) / v0)

        slip_condition = torch.abs(vrel) > eta
        trans_condition = torch.abs(disp + 2 * xi * vel) > mud * musd

        smooth_sign_vrel = torch.tanh(k_smooth * vrel)
        smooth_sign_Ffric = torch.tanh(k_smooth * Ffric)

        slip_vel = -disp - 2 * xi * vel - smooth_sign_vrel * Ffric
        trans_vel = -disp - 2 * xi * vel + mud * musd * smooth_sign_Ffric
        stick_vel = -(vel - v_d)

        dydt = torch.stack([
            torch.where(slip_condition | trans_condition, vel, v_d),
            torch.where(slip_condition, slip_vel, torch.where(
                trans_condition, trans_vel, stick_vel))
        ], dim=-1)

        return dydt

    def get_str(self) -> str:
        """
        Returns a string representation of the ODE system with its parameters.

        The string is constructed using multiple line f-string interpolation.
        """
        v_d = self.params["v_d"]
        xi = self.params["xi"]
        musd = self.params["musd"]
        mud = self.params["mud"]
        muv = self.params["muv"]
        v0 = self.params["v0"]

        description = (
            f"  ddisp/dt = vel\n"
            f"  dvel/dt  = -disp - 2*({xi})*vel - sign(vel - {v_d})*friction_law(...)\n"
            f"\n"
            f"Parameters:\n"
            f"  v_d  = {v_d}\n"
            f"  xi   = {xi}\n"
            f"  musd = {musd}\n"
            f"  mud  = {mud}\n"
            f"  muv  = {muv}\n"
            f"  v0   = {v0}\n"
        )
        return description
