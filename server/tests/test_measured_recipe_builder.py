"""Actual BRep metrology plus graph authoring using original non-VEX fixtures."""
import math

import pytest

from tachyon import assemblies as A
from tachyon.cad.metrology import measure_definition
from tachyon.errors import TachyonError
from tachyon.robots.builder import RecipeBuilder
from tachyon.robots.source_pack import MeasuredPart, SourcePack, native_pose


@pytest.fixture
def plate():
    import cadquery as cq
    shape=cq.Workplane("XY").box(80,40,4).faces(">Z").workplane().hole(4).val()
    component=cq.Assembly(shape,name="original-test-plate",metadata={"definitionName":"original-test-plate"})
    return MeasuredPart("original_plate","0:1:1:1","original-test-plate","1"*64,"structure",measure_definition(component))


def test_actual_brep_holes_require_the_measured_position_and_axis(plate):
    plate.port("top",(0.,0.,2.),(0.,0.,1.),(1.,0.,0.))
    assert plate.ports["top"].frame.point()==pytest.approx((0.,.002,0.))
    for point,axis,roll in (((10.,0.,2.),(0.,0.,1.),(1.,0.,0.)),((0.,0.,2.),(1.,0.,0.),(0.,1.,0.))):
        with pytest.raises(TachyonError) as caught:
            plate.port("not-a-measured-hole",point,axis,roll)
        assert caught.value.code=="UNMEASURED_MOUNT"


def test_purchased_datum_cannot_be_invented_outside_source_envelope(plate):
    with pytest.raises(TachyonError) as caught:
        plate.port("imaginary-mount",(100.,0.,0.),(0.,0.,1.),(1.,0.,0.),basis="purchased_interface")
    assert caught.value.code=="UNMEASURED_PURCHASED_INTERFACE"


def test_interface_identity_cannot_silently_move_between_revisions(plate):
    plate.port("face",(0.,0.,2.),(0.,0.,1.),(1.,0.,0.))
    with pytest.raises(ValueError,match="cannot change"):
        plate.port("face",(0.,0.,-2.),(0.,0.,1.),(1.,0.,0.))


def test_non_mating_fixed_placement_requires_a_declared_real_axial_stack(plate):
    plate.port("top",(0.,0.,2.),(0.,0.,1.),(1.,0.,0.))
    plate.port("bottom",(0.,0.,-2.),(0.,0.,1.),(1.,0.,0.))
    pack=SourcePack({"plate":plate})
    b=RecipeBuilder("original-stacked-plates","A",pack.builder_parts())
    b.root_part("base","plate","chassis",native_pose((0.,0.,0.)))
    for point in ((1.,0.,4.),(0.,0.,20.)):
        with pytest.raises(TachyonError) as caught:
            b.attach_at("rejected","plate","chassis","base","top","bottom",native_pose(point))
        assert caught.value.code=="NON_MATING_PLACEMENT"
    b.attach_at("second","plate","chassis","base","top","bottom",native_pose((0.,0.,4.)))
    assert len(b.instances)==2 and len(b.relationships)==1
    assert b.instances[1]["placementRelationshipId"]=="second-mount"


def test_native_pose_preserves_scale_and_handedness():
    transform=native_pose((100.,200.,300.),(0.,1.,0.),(0.,0.,1.),(1.,0.,0.))
    assert transform.point()==pytest.approx((.1,.2,.3))
    assert math.dist(transform.point(),transform.point((0.,1.,0.)))==pytest.approx(1.)
    with pytest.raises(ValueError,match="orthonormal"):
        native_pose((0.,0.,0.),(2.,0.,0.))


def test_independent_source_support_bounds_enclose_known_curved_geometry():
    import cadquery as cq
    from tachyon.cad.metrology import support_bounds_mm
    shape=cq.Workplane().sphere(20).val().translate((5.,-7.,3.))
    low,high=support_bounds_mm(shape)
    # Analytic sphere extrema, independent of GLB positions and source boxes.
    for observed,actual in zip(low,(-15.,-27.,-17.)):
        assert actual-.0011 <= observed <= actual
    for observed,actual in zip(high,(25.,13.,23.)):
        assert actual <= observed <= actual+.0011


def test_native_metrology_is_independent_of_previous_export_tessellation():
    import cadquery as cq
    from tachyon.cad.native import native_bounds_mm
    shape=cq.Workplane().sphere(50).val()
    before=native_bounds_mm(shape)
    shape.mesh(.5,.5)
    after=native_bounds_mm(shape)
    for actual,expected in zip(after,before):
        assert actual==pytest.approx(expected,abs=1e-8)
