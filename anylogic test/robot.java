package model;

import java.io.Serializable;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Calendar;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.Currency;
import java.util.Date;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Hashtable;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.ListIterator;
import java.util.Locale;
import java.util.Map;
import java.util.PriorityQueue;
import java.util.Random;
import java.util.Set;
import java.util.SortedMap;
import java.util.SortedSet;
import java.util.Stack;
import java.util.Timer;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.Vector;
import java.awt.Color;
import java.awt.Font;
import com.anylogic.engine.connectivity.ResultSet;
import com.anylogic.engine.connectivity.Statement;
import com.anylogic.engine.elements.*;
import com.anylogic.engine.markup.Network;
import com.anylogic.engine.Position;
import com.anylogic.engine.markup.PedFlowStatistics;
import com.anylogic.engine.markup.DensityMap;


import static java.lang.Math.*;
import static com.anylogic.engine.UtilitiesArray.*;
import static com.anylogic.engine.UtilitiesCollection.*;
import static com.anylogic.engine.presentation.UtilitiesColor.*;
import static com.anylogic.engine.HyperArray.*;

import com.anylogic.engine.*;
import com.anylogic.engine.analysis.*;
import com.anylogic.engine.connectivity.*;
import com.anylogic.engine.database.*;
import com.anylogic.engine.gis.*;
import com.anylogic.engine.markup.*;
import com.anylogic.engine.routing.*;
import com.anylogic.engine.presentation.*;
import com.anylogic.engine.gui.*;
import com.anylogic.engine.omniverse_connector.*;

import com.anylogic.libraries.modules.markup_descriptors.*;
import com.anylogic.libraries.modules.rack_system_module.*;
import com.anylogic.libraries.material_handling.*;
import com.anylogic.libraries.processmodeling.*;

import java.awt.geom.Arc2D;

public class Robot extends Agent
        implements ITransporter
{
  // Parameters

  private Collection<Object> generated_0_usd_list_xjal;
  private Collection<Object> generated_1_usd_list_xjal;
  @AnyLogicInternalCodegenAPI
  @Override
  public void createUsdObjects() {
    generated_0_usd_list_xjal.add(this.forklift);
    generated_1_usd_list_xjal.add(this.sittingWorker);
  }
  @AnyLogicInternalCodegenAPI
  @Override
  public void removeUsdObjects() {
    generated_0_usd_list_xjal.remove(this.forklift);
    generated_1_usd_list_xjal.remove(this.sittingWorker);
  }
  @AnyLogicInternalCodegenAPI
  private static Map<String, IElementDescriptor> elementDesciptors_xjal = createElementDescriptors( Robot.class );

  @AnyLogicInternalCodegenAPI
  @Override
  public Map<String, IElementDescriptor> getElementDesciptors() {
    return elementDesciptors_xjal;
  }
  @AnyLogicCustomProposalPriority(type = AnyLogicCustomProposalPriority.Type.STATIC_ELEMENT)
  public static final Scale scale = new Scale( 10.0 );

  @Override
  public Scale getScale() {
    return scale;
  }




  /** Internal constant, shouldn't be accessed by user */
  @AnyLogicInternalCodegenAPI
  protected static final int _STATECHART_COUNT_xjal = 0;


private double _datasetUpdateTime_xjal() {
	return time();
}
  // View areas
  public ViewArea _origin_VA = new ViewArea( this, "[Origin]", 0, 0, 1000.0, 600.0 );
  @Override
  @AnyLogicInternalCodegenAPI
  public int getViewAreas(Map<String, ViewArea> _output) {
    if ( _output != null ) {
      _output.put( "_origin_VA", this._origin_VA );
    }
    return 1 + super.getViewAreas( _output );
  }
  @AnyLogicInternalCodegenAPI
  protected static final Pair<String, Color>[] _forklift_customColors_xjal = new Pair[] {
    new Pair<String, Color>( "Material__2__Surf", null ),
    new Pair<String, Color>( "Material__1__Surf", null ),
  };
  @AnyLogicInternalCodegenAPI
  protected static final Pair<String, Color>[] _sittingWorker_customColors_xjal = new Pair[] {
    new Pair<String, Color>( "Material__5__Surf", null ),
    new Pair<String, Color>( "Material__9__Surf", null ),
    new Pair<String, Color>( "Material__7__Surf", null ),
    new Pair<String, Color>( "Material__6__Surf", null ),
    new Pair<String, Color>( "Material__2__Surf", null ),
    new Pair<String, Color>( "Material__3__Surf", null ),
    new Pair<String, Color>( "Material__8__Surf", null ),
    new Pair<String, Color>( "Material__4__Surf", null ),
  };
  @AnyLogicInternalCodegenAPI
  protected static final int _forklift = 1;
  @AnyLogicInternalCodegenAPI
  protected static final int _sittingWorker = 2;
  @AnyLogicInternalCodegenAPI
  protected static final int _forkliftWithWorker = 3;

  /** Internal constant, shouldn't be accessed by user */
  @AnyLogicInternalCodegenAPI
  protected static final int _SHAPE_NEXT_ID_xjal = 4;

  @AnyLogicInternalCodegenAPI
  public boolean isPublicPresentationDefined() {
    return true;
  }

  @AnyLogicInternalCodegenAPI
  public boolean isEmbeddedAgentPresentationVisible( Agent _a ) {
    return super.isEmbeddedAgentPresentationVisible( _a );
  }
  @AnyLogicInternalCodegenAPI
  private void _initialize_level_xjal() {
	  level.addAll(forkliftWithWorker);
  }

  
  /**
   * <i>This method should not be called by user</i>
   */
  @AnyLogicInternalCodegenAPI
  private void _forklift_SetDynamicParams_xjal( Shape3DObject shape ) {
    shape.setX(
-getScale().pixelsPerUnit(METER) 
);
  }
  
  protected Shape3DObject forklift;
  
  /**
   * <i>This method should not be called by user</i>
   */
  @AnyLogicInternalCodegenAPI
  private void _sittingWorker_SetDynamicParams_xjal( Shape3DObject shape ) {
    shape.setX(
-1.5 * getScale().pixelsPerUnit(METER) 
);
    shape.setZ(
0.8 * getScale().pixelsPerUnit(METER) 
);
  }
  
  protected Shape3DObject sittingWorker;
  protected ShapeGroup forkliftWithWorker;
  protected com.anylogic.engine.markup.Level level;

  private com.anylogic.engine.markup.Level[] _getLevels_xjal;

  @Override
  public com.anylogic.engine.markup.Level[] getLevels() {
    return _getLevels_xjal;
  }

  @AnyLogicInternalCodegenAPI
  private void _createPersistentElementsBP0_xjal() {
    forklift = new Shape3DObject(
		Robot.this, SHAPE_DRAW_2D3D, true, -10.0, 0.0, 0.0, 0.0,
			1.0, true, "/model/",
			"3d/forklift.dae", OBJECT_3D_YZX_AXIS_ORDER, Object3DInternalLighting.OBJECT_3D_INTERNAL_LIGHTING_OFF, false, -11.0, -6.0,
			21.0, 11.0, null, true, _forklift_customColors_xjal ) {
	
      @Override
	
      public void updateDynamicProperties() {
	
      _forklift_SetDynamicParams_xjal( this );
	
      super.updateDynamicProperties();
	
      }
    };
    sittingWorker = new Shape3DObject(
		Robot.this, SHAPE_DRAW_2D3D, true, -15.0, 0.0, 8.0, 0.0,
			1.0, true, "/model/",
			"3d/sittingworker.dae", OBJECT_3D_YZX_AXIS_ORDER, Object3DInternalLighting.OBJECT_3D_INTERNAL_LIGHTING_OFF, false, -2.0, -4.0,
			9.0, 7.0, null, true, _sittingWorker_customColors_xjal ) {
	
      @Override
	
      public void updateDynamicProperties() {
	
      _sittingWorker_SetDynamicParams_xjal( this );
	
      super.updateDynamicProperties();
	
      }
    };
  }

  @AnyLogicInternalCodegenAPI
  private void _createPersistentElementsAP0_xjal() {
    {
    forkliftWithWorker = new ShapeGroup( Robot.this, SHAPE_DRAW_2D3D, true, 0.0, 0.0, 0.0, 0.0
	
	     , forklift
	     , sittingWorker );
    }
  }

  @AnyLogicInternalCodegenAPI
  private void _createPersistentElementsBS0_xjal() {
  }



  // Static initialization of persistent elements
  private void instantiatePersistentElements_xjal() {
    level = new com.anylogic.engine.markup.Level(this, "level", SHAPE_DRAW_2D3D, 0.0, true, true);  			
	_getLevels_xjal = new com.anylogic.engine.markup.Level[] { 
      level };
    _createPersistentElementsBP0_xjal();
  }
  protected ShapeTopLevelPresentationGroup presentation;
  protected ShapeModelElementsGroup icon; 

  @Override
  @AnyLogicInternalCodegenAPI
  public ShapeTopLevelPresentationGroup getPresentationShape() {
    return presentation;
  }

  @Override
  @AnyLogicInternalCodegenAPI
  public ShapeModelElementsGroup getModelElementsShape() {
    return icon;
  }

	


  /**
   * Constructor
   */
  public Robot( Engine engine, Agent owner, AgentList<? extends Robot> ownerPopulation ) {
    super( engine, owner, ownerPopulation );
    instantiateBaseStructureThis_xjal();
  }

  @AnyLogicInternalCodegenAPI
  public void onOwnerChanged_xjal() {
    super.onOwnerChanged_xjal();
    setupReferences_xjal();
  }

  @AnyLogicInternalCodegenAPI
  public void instantiateBaseStructure_xjal() {
    super.instantiateBaseStructure_xjal();
    instantiateBaseStructureThis_xjal();
  }

  @AnyLogicInternalCodegenAPI
  private void instantiateBaseStructureThis_xjal() {
	instantiatePersistentElements_xjal();
    setupReferences_xjal();
  }

  @AnyLogicInternalCodegenAPI
  private void setupReferences_xjal() {
  }

  /**
   * Simple constructor. Please add created agent to some population by calling goToPopulation() function.
   */
  public Robot() {
  }

  @Override
  @AnyLogicInternalCodegenAPI
  public void doCreate() {
    super.doCreate();
    // Assigning initial values for plain variables
    setupPlainVariables_Robot_xjal();
Map<String, Set<?>> usdMapping = getRootAgent().ext(ExtRootModelAgent.class).getCustomObject(OmniverseHelper.USD_CONTEXT_COLLECTION_KEY,
()-> new LinkedHashMap<String, Set<?>>());
generated_0_usd_list_xjal = (Collection<Object>) 
usdMapping.computeIfAbsent("model.Robot.forklift",
(k)-> new LinkedHashSet<>());
			
		
generated_1_usd_list_xjal = (Collection<Object>) 
usdMapping.computeIfAbsent("model.Robot.sittingWorker",
(k)-> new LinkedHashSet<>());
			
		
    // Dynamic initialization of persistent elements
    _createPersistentElementsAP0_xjal();
	_initialize_level_xjal();
    level.initialize();
    presentation = new ShapeTopLevelPresentationGroup( Robot.this, true, 0, 0, 0, 0 , level );
    presentation.getConfiguration3D().setBackgroundColor( silver );
    icon = new ShapeModelElementsGroup( Robot.this, getElementProperty( "model.Robot.icon", IElementDescriptor.MODEL_ELEMENT_DESCRIPTORS )  );
    icon.setIconOffsets( 0.0, 0.0 );


    // Space setup
    {
      double _x_xjal = 
500 
;
      double _y_xjal = 
500 
;
      double _z_xjal = 
0 
;
      setupSpace( _x_xjal, _y_xjal, _z_xjal );
    }
    disableSteps();
    setNetworkUserDefined();
    setLayoutType( LAYOUT_USER_DEFINED );
	 // Port connectors with non-replicated objects
    // Creating replicated embedded objects
    setupInitialConditions_xjal( Robot.class );
    // Dynamic initialization of persistent elements
    _createPersistentElementsBS0_xjal();
  }

  @AnyLogicInternalCodegenAPI
  public void setupExt_xjal(AgentExtension _ext) {
    // Agent properties setup
    if ( _ext instanceof ExtAgentContinuous && tryExt(ExtAgentContinuous.class) == null ) {
      ExtAgentContinuous _e = (ExtAgentContinuous) _ext;
      _e.setAutomaticVerticalRotation( true );
    }
  }

  @Override
  @AnyLogicInternalCodegenAPI
  public void doStart() {
    super.doStart();
  }


  /**
   * Assigning initial values for plain variables<br>
   * <em>This method isn't designed to be called by user and may be removed in future releases.</em>
   */
  @AnyLogicInternalCodegenAPI
  public void setupPlainVariables_xjal() {
    setupPlainVariables_Robot_xjal();
  }

  /**
   * Assigning initial values for plain variables<br>
   * <em>This method isn't designed to be called by user and may be removed in future releases.</em>
   */
  @AnyLogicInternalCodegenAPI
  private void setupPlainVariables_Robot_xjal() {
  }

  // User API -----------------------------------------------------
  @AnyLogicInternalCodegenAPI
  public static LinkToAgentAnimationSettings _connections_commonAnimationSettings_xjal = new LinkToAgentAnimationSettingsImpl( false, black, 1.0, LINE_STYLE_SOLID, ARROW_NONE, 0.0 );

  public LinkToAgentCollection<Agent, Agent> connections = new LinkToAgentStandardImpl<Agent, Agent>(this, _connections_commonAnimationSettings_xjal);
  @Override
  public LinkToAgentCollection<? extends Agent, ? extends Agent> getLinkToAgentStandard_xjal() {
    return connections;
  }


  @AnyLogicInternalCodegenAPI
  public void drawLinksToAgents(boolean _underAgents_xjal, LinkToAgentAnimator _animator_xjal) {
    super.drawLinksToAgents(_underAgents_xjal, _animator_xjal);
    if ( _underAgents_xjal ) {
      _animator_xjal.drawLink( this, connections, true, true );
    }
  }

  public AgentList<? extends Robot> getPopulation() {
    return (AgentList<? extends Robot>) super.getPopulation();
  }

  public List<? extends Robot> agentsInRange( double distance ) {
    return (List<? extends Robot>) super.agentsInRange( distance );
  }


	public double getHomeX() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).getHomeX();
	}
	
	public double getHomeY() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).getHomeY();
	}
	
	public double getHomeZ() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).getHomeZ();
	}
	
	public INode getHomeLocation() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).getHomeLocation();
	}
	
	public double getHomeRotation() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).getHomeRotation();
	}
	
	public void setHomeLocation(INode home) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).setHomeLocation(home);
	}
	
	public void setHomePosition(double x, double y) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).setHomePosition(x, y);
	}
	
	public void setHomePosition(double x, double y, double z) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).setHomePosition(x, y, z);
	}
	
	public boolean isAttached() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).isAttached();
	}
	
	public void setAttached(boolean attached) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).setAttached(attached);
	}
	
	public boolean isReserved() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).isReserved();
	}
	
	public Agent getReservedBy() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).getReservedBy();
	}
	
	public Agent getServicedEntity() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).getServicedEntity();
	}
	
	public ResourceType getResourceType() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).getResourceType();
	}
	
	public ResourceUnitTask currentTask() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).currentTask();
	}
	
	public ResourceTaskType currentTaskType() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).currentTaskType();
	}
	
	public void addTask(ResourceUnitTask task) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).addTask(task);
	}
	
	public double mttr() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).mttr();
	}
	
	public double mttr(Downtime downtime) {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).mttr(downtime);
	}
	
	public double mttr(TimeUnits units) {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).mttr(units);
	}
	
	public double mttr(Downtime downtime, TimeUnits units) {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).mttr(downtime, units);
	}
	
	public double mtbf() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).mtbf();
	}
	
	public double mtbf(Downtime downtime) {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).mtbf(downtime);
	}
	
	public double mtbf(TimeUnits units) {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).mtbf(units);
	}
	
	public double mtbf(Downtime downtime, TimeUnits units) {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).mtbf(downtime, units);
	}
	
	public void removeTask(ResourceUnitTask task) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).removeTask(task);
	}
	
	public double getUtilization() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).getUtilization();
	}
	
	public void resetStats() {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).resetStats();
	}
	
	public double timeInState(ResourceUsageState state) {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).timeInState(state);
	}
	
	public double timeInState(ResourceUsageState state, TimeUnits units) {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).timeInState(state, units);
	}
	
	public double timeInState(TransporterState state, TimeUnits units) {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).timeInState(state, units);
	}
	
	public double timeInState(TransporterState state) {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).timeInState(state);
	}
	
	public boolean isBusy() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).isBusy();
	}
	
	public boolean isIdle() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).isIdle();
	}
	
	public ResourcePool resourcePool() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).resourcePool();
	}
	
	public com.anylogic.libraries.material_handling.TransporterFleet getFleet() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).getFleet();
	}
	
	public com.anylogic.libraries.material_handling.TransporterState getState() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).getState();
	}
	
	public com.anylogic.libraries.material_handling.ILocation getCurrentLocation() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).getCurrentLocation();
	}
		
	public double getMaximumSpeed(SpeedUnits units) {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).getMaximumSpeed(units);
	}
	
	public void setMaximumSpeed(double speed, SpeedUnits units) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).setMaximumSpeed(speed, units);
	}
	
	public double getMaximumSpeedOnCurvedSegment(SpeedUnits units) {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).getMaximumSpeedOnCurvedSegment(units);
	}
	
	public void setMaximumSpeedOnCurvedSegment(double speed, SpeedUnits units) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).setMaximumSpeedOnCurvedSegment(speed, units);
	}
	
	public double getAcceleration(AccelerationUnits units) {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).getAcceleration(units);
	}
	
	public void setAcceleration(double acceleration, AccelerationUnits units) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).setAcceleration(acceleration, units);
	}
	
	public double getDeceleration(AccelerationUnits units) {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).getDeceleration(units);
	}
	
	public void setDeceleration(double deceleration, AccelerationUnits units) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).setDeceleration(deceleration, units);
	}
	
	public Position getCargoPosition() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).getCargoPosition();
	}
	
	public void setCargoPosition(double dx, double dy, double dz, LengthUnits units) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).setCargoPosition(dx, dy, dz, units);
	}
	
	public void setCargoPosition(double dx, double dy, double dz, LengthUnits units, double rotation, double verticalRotation) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).setCargoPosition(dx, dy, dz, units, rotation, verticalRotation);
	}
	
	public void resetCargoPosition() {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).resetCargoPosition();
	}
	
	public void recalculateRoute() {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).recalculateRoute();
	}
	
	public void recalculateRoute(double x, double y, double z) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).recalculateRoute(x, y, z);
	}
	
	public void recalculateRoute(Level level, double x, double y, double z) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).recalculateRoute(level, x, y, z);
	}
	
	public void recalculateRoute(Node node) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).recalculateRoute(node);
	}
	
	public void recalculateRoute(Attractor attractor) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).recalculateRoute(attractor);
	}
	
	public void recalculateRoute(Path path, double offset, LengthUnits units) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).recalculateRoute(path, offset, units);
	}
	
	public void recalculateRoute(ConveyorPath conveyor, double offset, LengthUnits units) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).recalculateRoute(conveyor, offset, units);
	}
	
	public void recalculateRoute(PositionOnConveyor positionOnConveyor) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).recalculateRoute(positionOnConveyor);
	}
	
	public void recalculateRoute(ConveyorStation station) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).recalculateRoute(station);
	}
	
	public RouteData getRouteData() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).getRouteData();
	}
	
	public double getDistanceTravelled(LengthUnits units) {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).getDistanceTravelled(units);
	}
	
	public void resetDistanceTravelled() {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).resetDistanceTravelled();
	}
	
	public void ignoreCollisions(boolean ignore) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).ignoreCollisions(ignore);
	}
	
	public void ignoreCollisionsFor(double time, TimeUnits units) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).ignoreCollisionsFor(time, units);
	}
	
	public void move(Node node, TransporterState state) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).move(node, state);
	}
	
	public void move(double x, double y, TransporterState state) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).move(x, y, state);
	}
	
	public void move(Node node) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).move(node);
	}
	
	public void move(double x, double y) {
		ext(com.anylogic.libraries.material_handling.TransporterExtension.class).move(x, y);
	}
	
	@AnyLogicInternalAPI
	public double totalDowntime() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).totalDowntime();
	}
	
	@AnyLogicInternalAPI
	public double totalRepairTime() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).totalRepairTime();
	}

	@AnyLogicInternalAPI
	public double totalMaintenanceTime(){
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).totalMaintenanceTime();
	}

	@AnyLogicInternalAPI
	public double totalBreaksTime() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).totalBreaksTime();
	}

	@AnyLogicInternalAPI
	public double totalCustomTasksTime() {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).totalCustomTasksTime();
	}

	@AnyLogicInternalAPI
	public double totalDowntime(TimeUnits units) {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).totalDowntime(units);
	}

	@AnyLogicInternalAPI
	public double totalRepairTime(TimeUnits units) {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).totalRepairTime(units);
	}
	
	@AnyLogicInternalAPI
	public double totalMaintenanceTime(TimeUnits units) {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).totalMaintenanceTime(units);
	}

	@AnyLogicInternalAPI
	public double totalBreaksTime(TimeUnits units) {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).totalBreaksTime(units);
	}

	@AnyLogicInternalAPI
	public double totalCustomTasksTime(TimeUnits units) {
		return ext(com.anylogic.libraries.material_handling.TransporterExtension.class).totalCustomTasksTime(units);
	}
	
	@AnyLogicInternalAPI
	public void moveToNearestAgent( Iterable<? extends Agent> agents ) {
		super.moveToNearestAgent(agents);
	}
	
	@AnyLogicInternalAPI
	public void moveToNearestAgent( Iterable<? extends Agent> agents, double tripTime ) {
		super.moveToNearestAgent( agents, tripTime );
	}
	
	@AnyLogicInternalAPI
	public void moveToStraight(double x, double y) {
	    super.moveToStraight(x, y);
	}
	
	@AnyLogicInternalAPI
	public void moveToStraight(Point location) {
	    super.moveToStraight(location);
	}
	
	@AnyLogicInternalAPI
	public void moveToStraight(Agent agent) {
	    super.moveToStraight(agent);
	}
	
	@AnyLogicInternalAPI
	public void moveToStraightInTime(Point location, double tripTime) {
	    super.moveToStraightInTime(location, tripTime);
	}
	
	@AnyLogicInternalAPI
	public void moveToStraightInTime(Point location, double tripTime, TimeUnits units) {
	    super.moveToStraightInTime(location, tripTime, units);
	}
	
	@AnyLogicInternalAPI
	public void moveTo(double x, double y) {
	    super.moveTo(x, y);
	}
	
	@AnyLogicInternalAPI
	public void moveToInTime(double x, double y, double tripTime) {
	    super.moveToInTime(x, y, tripTime);
	}
	
	@AnyLogicInternalAPI
	public void moveToInTime(double x, double y, double tripTime, TimeUnits units) {
	    super.moveToInTime(x, y, tripTime, units);
	}
	
	@AnyLogicInternalAPI
	public void moveTo( Point location ) {
	    super.moveTo( location );
	}
	
	@AnyLogicInternalAPI
	public void moveTo( Agent agent ) {
	    super.moveTo( agent );
	}
	
	@AnyLogicInternalAPI
	public void moveToInTime(Agent agent, double tripTime){
	    super.moveToInTime( agent, tripTime );
	}
	
	@AnyLogicInternalAPI
	public void moveToInTime(Agent agent, double tripTime, TimeUnits units){
	    super.moveToInTime( agent, tripTime, units );
	}
	
	@AnyLogicInternalAPI
	public void moveTo(String geographicPlace) {
	    super.moveTo(geographicPlace);
	}
	
	@AnyLogicInternalAPI
	public void moveToInTime(Point location, double tripTime){
	    super.moveToInTime(location, tripTime);
	}
	
	@AnyLogicInternalAPI
	public void moveToInTime(Point location, double tripTime, TimeUnits units){
	    super.moveToInTime(location, tripTime, units);
	}
	
	@AnyLogicInternalAPI
	public void moveTo( INode node ) {
	    super.moveTo(node);
	}
	
	@AnyLogicInternalAPI
	public void moveTo( INode node, Point location ) {
	    super.moveTo(node, location);
	}
	
	@AnyLogicInternalAPI
	public void moveToInTime( INode node, double tripTime ) {
	    super.moveToInTime(node, tripTime);
	}
	
	@AnyLogicInternalAPI
	public void moveToInTime( INode node, double tripTime, TimeUnits units ) {
	    super.moveToInTime(node, null, tripTime, units);
	}
	
	@AnyLogicInternalAPI
	public void moveToInTime( INode node, Point location, double tripTime ) {
	    super.moveToInTime(node, location, tripTime);
	}
	
	@AnyLogicInternalAPI
	public void moveToInTime( INode node, Point location, double tripTime, TimeUnits units ) {
	    super.moveToInTime(node, location, tripTime, units);
	}
	
	@AnyLogicInternalAPI
	public void moveTo( Attractor attractor ) {
	    super.moveTo(attractor);
	}
	
	@AnyLogicInternalAPI
	public void moveToInTime( Attractor attractor, double tripTime ) {
	    super.moveToInTime(attractor, tripTime);
	}
	
	@AnyLogicInternalAPI
	public void moveToInTime( Attractor attractor, double tripTime, TimeUnits units ) {
	    super.moveToInTime(attractor, tripTime, units);
	}
	
	@AnyLogicInternalAPI
	public void moveToStraight(double x, double y, double z) {
	    super.moveToStraight(x, y, z);
	}
	
	@AnyLogicInternalAPI
	public void moveToStraightInTime(double x, double y, double z, double tripTime) {
	    super.moveToStraightInTime(x, y, z, tripTime);
	}
	
	@AnyLogicInternalAPI
	public void moveToStraightInTime(double x, double y, double z, double tripTime, TimeUnits units) {
	    super.moveToStraightInTime(x, y, z, tripTime, units);
	}
	
	@AnyLogicInternalAPI
	public void moveTo( double x, double y, double z ) {
	    super.moveTo( x, y, z );
	}
	
	@AnyLogicInternalAPI
	public void moveToInTime( double x, double y, double z, double tripTime ) {
	    super.moveToInTime( x, y, z, tripTime );
	}
	
	@AnyLogicInternalAPI
	public void moveToInTime( double x, double y, double z, double tripTime, TimeUnits units ) {
	    super.moveToInTime( x, y, z, tripTime, units );
	}
	
	@AnyLogicInternalAPI
	public void moveTo(double x, double y, Path2D path) {
	    super.moveTo( x, y, path );
	}
	
	@AnyLogicInternalAPI
	public void moveToInTime(double x, double y, Path2D path, double tripTime) {
	    super.moveToInTime(x, y, path, tripTime);
	}
	
	@AnyLogicInternalAPI
	public void moveToInTime(double x, double y, Path2D path, double tripTime, TimeUnits units) {
	    super.moveToInTime(x, y, path, tripTime, units);
	}
	
	@AnyLogicInternalAPI
	public void moveTo(Point location, Path3D path) {
	    super.moveTo(location, path);
	}
	
	@AnyLogicInternalAPI
	public void moveToInTime(Point location, Path3D path, double tripTime) {
	    super.moveToInTime(location, path, tripTime);
	}
	
	@AnyLogicInternalAPI
	public void moveToInTime(Point location, Path3D path, double tripTime, TimeUnits units) {
	    super.moveToInTime(location, path, tripTime, units);
	}
	
	@AnyLogicInternalAPI
	public void moveTo(double x, double y, double z, Path3D path) {
	    super.moveTo(x, y, z, path);
	}
	
	@AnyLogicInternalAPI
	public void moveToInTime(double x, double y, double z, Path3D path, double tripTime) {
	    super.moveToInTime(x, y, z, path, tripTime);
	}
	
	@AnyLogicInternalAPI
	public void moveToInTime(double x, double y, double z, Path3D path, double tripTime, TimeUnits units) {
	    super.moveToInTime(x, y, z, path, tripTime, units);
	}
	
	@AnyLogicInternalAPI
	public void moveToNextCell( CellDirection dir ) {
		super.moveToNextCell(dir);
	}
	
}
