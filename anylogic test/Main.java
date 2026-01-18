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

public class Main extends Agent
{
  // Parameters
  // Plain Variables

  public 
double 
 variable;
  public 
double 
 inventory;
  public 
double 
 order_quantity;
  public 
int 
 day_index;

  @AnyLogicInternalCodegenAPI
  private static Map<String, IElementDescriptor> elementDesciptors_xjal = createElementDescriptors( Main.class );

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


  // Events

  public EventTimeout DailyUpdate = new EventTimeout(this);

  @Override
  @AnyLogicInternalCodegenAPI
  public String getNameOf( EventTimeout _e ) {
     if( _e == DailyUpdate ) return "DailyUpdate";
    return super.getNameOf( _e );
  }

  @Override
  @AnyLogicInternalCodegenAPI
  public EventTimeout.Mode getModeOf( EventTimeout _e ) {
    if ( _e == DailyUpdate ) return EVENT_TIMEOUT_MODE_CYCLIC;
    return super.getModeOf( _e );
  }

  @Override
  @AnyLogicInternalCodegenAPI
  public double getFirstOccurrenceTime( EventTimeout _e ) {
    double _t;
    if ( _e == DailyUpdate ) {
      _t = 
1 
;
      _t = toModelTime( _t, SECOND );
      return _t;
    }
    return super.getFirstOccurrenceTime( _e );
  }

  @Override
  @AnyLogicInternalCodegenAPI
  public double evaluateTimeoutOf( EventTimeout _e ) {
    double _t;
    if( _e == DailyUpdate) {
      _t = 
1 
;
      _t = toModelTime( _t, MINUTE );
      return _t;
    }
    return super.evaluateTimeoutOf( _e );
  }

  @Override
  @AnyLogicInternalCodegenAPI
  public void executeActionOf( EventTimeout _e ) {
    if ( _e == DailyUpdate ) {
      EventTimeout self = _e;

// Logic to manage daily flow
// 1. Calculate Demand
int dayOfWeek = day_index % 7;
int demand;
if (dayOfWeek < 5) demand = uniform_discr(5, 15);      // Weekday
else if (dayOfWeek == 5) demand = uniform_discr(15, 30); // Sat
else demand = uniform_discr(30, 50);                   // Sun
// 2. Consume Inventory (Logic)
double sold = Math.min(inventory, demand);
inventory -= sold;
// 3. Call AI
getPrediction();
// 4. Order & Inject
inventory += order_quantity;
if (order_quantity > 0) {
    sourceOrder.inject(1); // One pallet per order
}
// 5. Logging
traceln("Day " + day_index + " (" + dayOfWeek + ") | Demand: " + demand + 
        " | Sold: " + sold + " | Ordered: " + order_quantity);
day_index++; 
;
      return;
    }
    super.executeActionOf( _e );
  }


  /** Internal constant, shouldn't be accessed by user */
  @AnyLogicInternalCodegenAPI
  protected static final int _STATECHART_COUNT_xjal = 0;


  // Embedded Objects

  public com.anylogic.libraries.material_handling.TransporterFleet<
Robot 
> robots;
  public com.anylogic.libraries.processmodeling.Source<
Agent 
> sourceOrder;
  public com.anylogic.libraries.processmodeling.Sink<
Agent 
> sinkOrder;
  public com.anylogic.libraries.material_handling.Store<
Agent 
> storeInRack;
  public com.anylogic.libraries.material_handling.Retrieve<
Agent 
> pickFromRack;
  public com.anylogic.libraries.modules.rack_system_module.StorageDescriptor _storageSystem_controller_xjal;

  public String getNameOf( Agent ao ) {
    if ( ao == robots ) return "robots";
    if ( ao == sourceOrder ) return "sourceOrder";
    if ( ao == sinkOrder ) return "sinkOrder";
    if ( ao == storeInRack ) return "storeInRack";
    if ( ao == pickFromRack ) return "pickFromRack";
    if ( ao == _storageSystem_controller_xjal ) return "_storageSystem_controller_xjal";
    return super.getNameOf( ao );
  }

  public AgentAnimationSettings getAnimationSettingsOf( Agent ao ) {
    return super.getAnimationSettingsOf( ao );
  }


  public String getNameOf( AgentList<?> aolist ) {
    return super.getNameOf( aolist );
  }
  
  public AgentAnimationSettings getAnimationSettingsOf( AgentList<?> aolist ) {
    return super.getAnimationSettingsOf( aolist );
  }


  /**
   * Creates an embedded object instance<br>
   * <i>This method should not be called by user</i>
   */
  protected com.anylogic.libraries.material_handling.TransporterFleet<Robot> instantiate_robots_xjal() {
    com.anylogic.libraries.material_handling.TransporterFleet<Robot> _result_xjal = new com.anylogic.libraries.material_handling.TransporterFleet<Robot>( getEngine(), this, null ) {
      @Override
      public Agent newTransporter(  ) {
        return _robots_newTransporter_xjal( this );
      }
      @Override
      public double maximumSpeed( Robot unit ) {
        return _robots_maximumSpeed_xjal( this, unit );
      }

      @AnyLogicInternalCodegenAPI
      public SpeedUnits getUnitsForCodeOf_maximumSpeed() {
        return MPS;
      }
      @Override
      public double acceleration( Robot unit ) {
        return _robots_acceleration_xjal( this, unit );
      }

      @AnyLogicInternalCodegenAPI
      public AccelerationUnits getUnitsForCodeOf_acceleration() {
        return MPS_SQ;
      }
      @Override
      public double deceleration( Robot unit ) {
        return _robots_deceleration_xjal( this, unit );
      }

      @AnyLogicInternalCodegenAPI
      public AccelerationUnits getUnitsForCodeOf_deceleration() {
        return MPS_SQ;
      }
	};
    
    return _result_xjal;
  }

  /**
   * Setups parameters of an embedded object instance<br>
   * This method should not be called by user
   */
  private void setupParameters_robots_xjal( final com.anylogic.libraries.material_handling.TransporterFleet<Robot> self, TableInput _t ) {
    self.navigationType = self._navigationType_DefaultValue_xjal();
    self.recognizeAllTransporters = self._recognizeAllTransporters_DefaultValue_xjal();
    self.capacityDefinitionType = self._capacityDefinitionType_DefaultValue_xjal();
    self.capacity = self._capacity_DefaultValue_xjal();
    self.capacitySchedule = self._capacitySchedule_DefaultValue_xjal();
    self.homeNodes = new Node[]
{ receivingDock, shippingDock } 
;
    self.turnRadius = self._turnRadius_DefaultValue_xjal();
    self.minDistanceToObstacle = self._minDistanceToObstacle_DefaultValue_xjal();
    self.isSpeedLimitedNearObstacle = self._isSpeedLimitedNearObstacle_DefaultValue_xjal();
    self.delayToResumeMovement = self._delayToResumeMovement_DefaultValue_xjal();
    self.downtimes = self._downtimes_DefaultValue_xjal();
    self.customRouting = self._customRouting_DefaultValue_xjal();
    self.addToCustomPopulation = self._addToCustomPopulation_DefaultValue_xjal();
  }

  /**
   * Setups an embedded object instance<br>
   * This method should not be called by user
   */
  @AnyLogicInternalCodegenAPI
  private void doBeforeCreate_robots_xjal( com.anylogic.libraries.material_handling.TransporterFleet<Robot> self, TableInput _t ) {
  }
  /**
   * Creates an embedded object instance<br>
   * <i>This method should not be called by user</i>
   */
  protected com.anylogic.libraries.processmodeling.Source<Agent> instantiate_sourceOrder_xjal() {
    com.anylogic.libraries.processmodeling.Source<Agent> _result_xjal = new com.anylogic.libraries.processmodeling.Source<Agent>( getEngine(), this, null ) {
      @Override
      public Attractor locationAttractor( Agent agent ) {
        return _sourceOrder_locationAttractor_xjal( this, agent );
      }
      @Override
      public double speed( Agent agent ) {
        return _sourceOrder_speed_xjal( this, agent );
      }

      @AnyLogicInternalCodegenAPI
      public SpeedUnits getUnitsForCodeOf_speed() {
        return MPS;
      }
	};
    
    return _result_xjal;
  }

  /**
   * Setups parameters of an embedded object instance<br>
   * This method should not be called by user
   */
  private void setupParameters_sourceOrder_xjal( final com.anylogic.libraries.processmodeling.Source<Agent> self, TableInput _t ) {
    self.arrivalType = 
self.MANUAL 
;
    self.rate = self._rate_DefaultValue_xjal();
    self.firstArrivalMode = self._firstArrivalMode_DefaultValue_xjal();
    self.firstArrivalTime = self._firstArrivalTime_DefaultValue_xjal();
    self.rateSchedule = self._rateSchedule_DefaultValue_xjal();
    self.modifyRate = self._modifyRate_DefaultValue_xjal();
    self.arrivalSchedule = self._arrivalSchedule_DefaultValue_xjal();
    self.setAgentParametersFromDB = self._setAgentParametersFromDB_DefaultValue_xjal();
    self.databaseTable = self._databaseTable_DefaultValue_xjal();
    self.multipleEntitiesPerArrival = self._multipleEntitiesPerArrival_DefaultValue_xjal();
    self.limitArrivals = self._limitArrivals_DefaultValue_xjal();
    self.maxArrivals = self._maxArrivals_DefaultValue_xjal();
    self.locationType = 
self.LOCATION_ATTRACTOR 
;
    self.locationXYZInNetwork = self._locationXYZInNetwork_DefaultValue_xjal();
    self.enableCustomStartTime = self._enableCustomStartTime_DefaultValue_xjal();
    self.startTime = self._startTime_DefaultValue_xjal();
    self.addToCustomPopulation = self._addToCustomPopulation_DefaultValue_xjal();
    self.pushProtocol = self._pushProtocol_DefaultValue_xjal();
    self.discardHangingEntities = self._discardHangingEntities_DefaultValue_xjal();
  }

  /**
   * Setups an embedded object instance<br>
   * This method should not be called by user
   */
  @AnyLogicInternalCodegenAPI
  private void doBeforeCreate_sourceOrder_xjal( com.anylogic.libraries.processmodeling.Source<Agent> self, TableInput _t ) {
  }
  /**
   * Creates an embedded object instance<br>
   * <i>This method should not be called by user</i>
   */
  protected com.anylogic.libraries.processmodeling.Sink<Agent> instantiate_sinkOrder_xjal() {
    com.anylogic.libraries.processmodeling.Sink<Agent> _result_xjal = new com.anylogic.libraries.processmodeling.Sink<Agent>( getEngine(), this, null );
    
    return _result_xjal;
  }

  /**
   * Setups parameters of an embedded object instance<br>
   * This method should not be called by user
   */
  private void setupParameters_sinkOrder_xjal( final com.anylogic.libraries.processmodeling.Sink<Agent> self, TableInput _t ) {
  }

  /**
   * Setups an embedded object instance<br>
   * This method should not be called by user
   */
  @AnyLogicInternalCodegenAPI
  private void doBeforeCreate_sinkOrder_xjal( com.anylogic.libraries.processmodeling.Sink<Agent> self, TableInput _t ) {
  }
  /**
   * Creates an embedded object instance<br>
   * <i>This method should not be called by user</i>
   */
  protected com.anylogic.libraries.material_handling.Store<Agent> instantiate_storeInRack_xjal() {
    com.anylogic.libraries.material_handling.Store<Agent> _result_xjal = new com.anylogic.libraries.material_handling.Store<Agent>( getEngine(), this, null ) {
      @Override
      public com.anylogic.libraries.material_handling.TransporterFleet fleet( Agent agent ) {
        return _storeInRack_fleet_xjal( this, agent );
      }
      @Override
      public Node seizeDestinationNode( Agent agent, Agent unit ) {
        return _storeInRack_seizeDestinationNode_xjal( this, agent, unit );
      }
      @Override
      public RackUnitAggregator storage( Agent agent ) {
        return _storeInRack_storage_xjal( this, agent );
      }
      @Override
      public double elevationSpeed( Agent agent, Agent unit ) {
        return _storeInRack_elevationSpeed_xjal( this, agent, unit );
      }

      @AnyLogicInternalCodegenAPI
      public SpeedUnits getUnitsForCodeOf_elevationSpeed() {
        return MPS;
      }
	};
    
    return _result_xjal;
  }

  /**
   * Setups parameters of an embedded object instance<br>
   * This method should not be called by user
   */
  private void setupParameters_storeInRack_xjal( final com.anylogic.libraries.material_handling.Store<Agent> self, TableInput _t ) {
    self.useAlreadySeized = self._useAlreadySeized_DefaultValue_xjal();
    self.resourceType = self._resourceType_DefaultValue_xjal();
    self.seizeDestinationType = 
self.PICKUP_NODE 
;
    self.slottingPolicy = 
self.SP_RANDOM_AVAILABLE 
;
    self.moveAgentTo = self._moveAgentTo_DefaultValue_xjal();
    self.releaseDestinationType = self._releaseDestinationType_DefaultValue_xjal();
    self.movingGoHome = self._movingGoHome_DefaultValue_xjal();
    self.customizeTransporterChoice = self._customizeTransporterChoice_DefaultValue_xjal();
    self.dispatchingPolicy = self._dispatchingPolicy_DefaultValue_xjal();
    self.customizeResourceChoice = self._customizeResourceChoice_DefaultValue_xjal();
  }

  /**
   * Setups an embedded object instance<br>
   * This method should not be called by user
   */
  @AnyLogicInternalCodegenAPI
  private void doBeforeCreate_storeInRack_xjal( com.anylogic.libraries.material_handling.Store<Agent> self, TableInput _t ) {
  }
  /**
   * Creates an embedded object instance<br>
   * <i>This method should not be called by user</i>
   */
  protected com.anylogic.libraries.material_handling.Retrieve<Agent> instantiate_pickFromRack_xjal() {
    com.anylogic.libraries.material_handling.Retrieve<Agent> _result_xjal = new com.anylogic.libraries.material_handling.Retrieve<Agent>( getEngine(), this, null ) {
      @Override
      public com.anylogic.libraries.material_handling.TransporterFleet fleet( Agent agent ) {
        return _pickFromRack_fleet_xjal( this, agent );
      }
      @Override
      public Node destinationNodeTransporter( Agent agent, Agent unit ) {
        return _pickFromRack_destinationNodeTransporter_xjal( this, agent, unit );
      }
      @Override
      public double loweringSpeed( Agent agent, Agent unit ) {
        return _pickFromRack_loweringSpeed_xjal( this, agent, unit );
      }

      @AnyLogicInternalCodegenAPI
      public SpeedUnits getUnitsForCodeOf_loweringSpeed() {
        return MPS;
      }
	};
    
    return _result_xjal;
  }

  /**
   * Setups parameters of an embedded object instance<br>
   * This method should not be called by user
   */
  private void setupParameters_pickFromRack_xjal( final com.anylogic.libraries.material_handling.Retrieve<Agent> self, TableInput _t ) {
    self.resourceType = self._resourceType_DefaultValue_xjal();
    self.retrieveFromDeepPosition = self._retrieveFromDeepPosition_DefaultValue_xjal();
    self.destinationType = self._destinationType_DefaultValue_xjal();
    self.destinationTypeTransporter = self._destinationTypeTransporter_DefaultValue_xjal();
    self.takeAgentFrom = self._takeAgentFrom_DefaultValue_xjal();
    self.transporterReleaseDestinationType = self._transporterReleaseDestinationType_DefaultValue_xjal();
    self.customizeResourceChoice = self._customizeResourceChoice_DefaultValue_xjal();
    self.customizeTransporterChoice = self._customizeTransporterChoice_DefaultValue_xjal();
    self.dispatchingPolicy = self._dispatchingPolicy_DefaultValue_xjal();
  }

  /**
   * Setups an embedded object instance<br>
   * This method should not be called by user
   */
  @AnyLogicInternalCodegenAPI
  private void doBeforeCreate_pickFromRack_xjal( com.anylogic.libraries.material_handling.Retrieve<Agent> self, TableInput _t ) {
  }
  /**
   * Creates an embedded object instance<br>
   * <i>This method should not be called by user</i>
   */
  protected com.anylogic.libraries.modules.rack_system_module.StorageDescriptor instantiate__storageSystem_controller_xjal_xjal() {
    com.anylogic.libraries.modules.rack_system_module.StorageDescriptor _result_xjal = new com.anylogic.libraries.modules.rack_system_module.StorageDescriptor( getEngine(), this, null );
    
    return _result_xjal;
  }

  /**
   * Setups parameters of an embedded object instance<br>
   * This method should not be called by user
   */
  private void setupParameters__storageSystem_controller_xjal_xjal( final com.anylogic.libraries.modules.rack_system_module.StorageDescriptor _self, TableInput _t ) {
    Storage self = storageSystem;
    _self.specifiedInslotSpeed = _self._specifiedInslotSpeed_DefaultValue_xjal();
    _self.inslotSpeed = _self._inslotSpeed_DefaultValue_xjal();
    _self.restrictedAisleAccess = _self._restrictedAisleAccess_DefaultValue_xjal();
    _self.aisleCapacityRestriction = _self._aisleCapacityRestriction_DefaultValue_xjal();
  }

  /**
   * Setups an embedded object instance<br>
   * This method should not be called by user
   */
  @AnyLogicInternalCodegenAPI
  private void doBeforeCreate__storageSystem_controller_xjal_xjal( com.anylogic.libraries.modules.rack_system_module.StorageDescriptor self, TableInput _t ) {
  }

  private Agent _robots_newTransporter_xjal( final com.anylogic.libraries.material_handling.TransporterFleet<Robot> self ) {
    Agent _value;
    _value = 
new model.Robot() 
;
    return _value;
  }
  private double _robots_maximumSpeed_xjal( final com.anylogic.libraries.material_handling.TransporterFleet<Robot> self, Robot unit ) {
    double _value;
    _value = 
100

 
;
    return _value;
  }
  private double _robots_acceleration_xjal( final com.anylogic.libraries.material_handling.TransporterFleet<Robot> self, Robot unit ) {
    double _value;
    _value = 
5 
;
    return _value;
  }
  private double _robots_deceleration_xjal( final com.anylogic.libraries.material_handling.TransporterFleet<Robot> self, Robot unit ) {
    double _value;
    _value = 
2 
;
    return _value;
  }
  private Attractor _sourceOrder_locationAttractor_xjal( final com.anylogic.libraries.processmodeling.Source<Agent> self, Agent agent ) {
    Attractor _value;
    _value = 
attractor10 
;
    return _value;
  }
  private double _sourceOrder_speed_xjal( final com.anylogic.libraries.processmodeling.Source<Agent> self, Agent agent ) {
    double _value;
    _value = 
2
 
;
    return _value;
  }
  private com.anylogic.libraries.material_handling.TransporterFleet _storeInRack_fleet_xjal( final com.anylogic.libraries.material_handling.Store<Agent> self, Agent agent ) {
    com.anylogic.libraries.material_handling.TransporterFleet _value;
    _value = 
robots 
;
    return _value;
  }
  private Node _storeInRack_seizeDestinationNode_xjal( final com.anylogic.libraries.material_handling.Store<Agent> self, Agent agent, Agent unit ) {
    Node _value;
    _value = 
receivingDock 
;
    return _value;
  }
  private RackUnitAggregator _storeInRack_storage_xjal( final com.anylogic.libraries.material_handling.Store<Agent> self, Agent agent ) {
    RackUnitAggregator _value;
    _value = 
storageSystem 
;
    return _value;
  }
  private double _storeInRack_elevationSpeed_xjal( final com.anylogic.libraries.material_handling.Store<Agent> self, Agent agent, Agent unit ) {
    double _value;
    _value = 
5
 
;
    return _value;
  }
  private com.anylogic.libraries.material_handling.TransporterFleet _pickFromRack_fleet_xjal( final com.anylogic.libraries.material_handling.Retrieve<Agent> self, Agent agent ) {
    com.anylogic.libraries.material_handling.TransporterFleet _value;
    _value = 
robots 
;
    return _value;
  }
  private Node _pickFromRack_destinationNodeTransporter_xjal( final com.anylogic.libraries.material_handling.Retrieve<Agent> self, Agent agent, Agent unit ) {
    Node _value;
    _value = 
shippingDock 
;
    return _value;
  }
  private double _pickFromRack_loweringSpeed_xjal( final com.anylogic.libraries.material_handling.Retrieve<Agent> self, Agent agent, Agent unit ) {
    double _value;
    _value = 
5 
;
    return _value;
  }
  // Functions

  void getPrediction(  ) { 

try {
    // 1. Prepare JSON
    int dow = day_index % 7;
    
    // --- FIXED: Default to 0.0 to prevent compilation errors ---
    // TODO: Replace 0.0 with your actual variable names if you have them (e.g. totalDemand)
    double prevDemand = 0.0; 
    double prevSold = 0.0;
    // -----------------------------------------------------------

    // Use Locale.US to ensure dot separates decimals (e.g. "10.5" not "10,5")
    String jsonInput = String.format(java.util.Locale.US, 
        "{\"inventory\": %.1f, \"day_index\": %d, \"day_of_week\": %d, \"previous_demand\": %.1f, \"previous_sold\": %.1f}", 
        inventory, day_index, dow, prevDemand, prevSold
    );
    
    // 2. Send Request
    java.net.URL url = new java.net.URL("http://127.0.0.1:8000/predict");
    java.net.HttpURLConnection con = (java.net.HttpURLConnection) url.openConnection();
    con.setRequestMethod("POST");
    con.setRequestProperty("Content-Type", "application/json");
    con.setDoOutput(true);
    
    try(java.io.OutputStream os = con.getOutputStream()) {
        os.write(jsonInput.getBytes("utf-8"));
    }
    
    // 3. Read Response
    java.io.BufferedReader br = new java.io.BufferedReader(new java.io.InputStreamReader(con.getInputStream(), "utf-8"));
    StringBuilder responseBuilder = new StringBuilder();
    String line;
    while ((line = br.readLine()) != null) {
        responseBuilder.append(line);
    }
    String response = responseBuilder.toString();
    
    // 4. PARSE 1: Get Order Quantity
    if (response != null && response.contains("\"order_quantity\":")) {
        int startKey = response.indexOf("\"order_quantity\":");
        int startVal = startKey + 17; // length of key
        int endVal = response.indexOf(",", startVal);
        if (endVal == -1) endVal = response.indexOf("}", startVal);
        
        String numStr = response.substring(startVal, endVal).trim();
        numStr = numStr.replaceAll("[^0-9.]", ""); 
        
        if (numStr.length() > 0) {
            order_quantity = Double.parseDouble(numStr);
        }
    }

    // 5. PARSE 2: Get and Print Formatted Log
    if (response != null && response.contains("\"formatted_log\":")) {
        int startKey = response.indexOf("\"formatted_log\":");
        int startQuote = response.indexOf("\"", startKey + 16);
        
        if (startQuote != -1) {
            int endQuote = startQuote + 1;
            boolean escape = false;
            while (endQuote < response.length()) {
                char c = response.charAt(endQuote);
                if (c == '\\') {
                    escape = !escape;
                } else if (c == '"' && !escape) {
                    break;
                } else {
                    escape = false;
                }
                endQuote++;
            }
            
            if (endQuote < response.length()) {
                String logStr = response.substring(startQuote + 1, endQuote);
                logStr = logStr.replace("\\n", "\n").replace("\\t", "\t").replace("\\\"", "\"");
                traceln(logStr);
            }
        }
    }

} catch (Exception e) {
    traceln("AI Error: " + e.getMessage());
    e.printStackTrace();
} 
  }
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
  /** Internal constant, shouldn't be accessed by user */
  @AnyLogicInternalCodegenAPI
  protected static final int _SHAPE_NEXT_ID_xjal = 1;

  @AnyLogicInternalCodegenAPI
  public boolean isPublicPresentationDefined() {
    return true;
  }

  @AnyLogicInternalCodegenAPI
  public boolean isEmbeddedAgentPresentationVisible( Agent _a ) {
    return super.isEmbeddedAgentPresentationVisible( _a );
  }
  @AnyLogicInternalCodegenAPI
  private void _initialize_network_xjal() {
	  network.addAll(receivingDock, path, shippingDock);
  }
  @AnyLogicInternalCodegenAPI
  private void _initialize_level_xjal() {
	  level.addAll(storageSystem, network);
  }
  @AnyLogicInternalCodegenAPI
  protected static final double[] _receivingDock_pointsDX_xjal() {
    return new double[] {  };
  }

  @AnyLogicInternalCodegenAPI
  protected static final double[] _receivingDock_pointsDY_xjal() {
    return new double[] {  };
  }
  @AnyLogicInternalCodegenAPI
  private Attractor[] _receivingDock_attractors_xjal() {
    return new Attractor[] {
        attractor10, 
    };
  }
  @AnyLogicInternalCodegenAPI
  protected static final double[] _shippingDock_pointsDX_xjal() {
    return new double[] {  };
  }

  @AnyLogicInternalCodegenAPI
  protected static final double[] _shippingDock_pointsDY_xjal() {
    return new double[] {  };
  }
  @AnyLogicInternalCodegenAPI
  private Attractor[] _shippingDock_attractors_xjal() {
    return new Attractor[] {
        attractor, 
    };
  }

  protected Storage storageSystem;
  protected Attractor attractor10;
  protected RectangularNode<Agent> receivingDock;
  protected Path path;
  protected Attractor attractor;
  protected RectangularNode<Agent> shippingDock;
  protected com.anylogic.engine.markup.Network network;

  private INetwork[] _getNetworks_xjal;

  @Override
  public INetwork[] getNetworks() {
    return _getNetworks_xjal;
  }

  protected com.anylogic.engine.markup.Level level;

  private com.anylogic.engine.markup.Level[] _getLevels_xjal;

  @Override
  public com.anylogic.engine.markup.Level[] getLevels() {
    return _getLevels_xjal;
  }

  @AnyLogicInternalCodegenAPI
  private void _createPersistentElementsBP0_xjal() {
    attractor10 = new Attractor( 40.0, 30.0, 0.0 );
    path = new Path( this, SHAPE_DRAW_2D3D, true, true, false, 10, false, 10, PATH_DASHEDLINE, dodgerBlue, 1.0,
			convertMarkupSegmentDescriptors_xjal(this.<MarkupSegmentDescriptor[]>getElementProperty("path", IElementDescriptor.MARKUP_SEGMENTS)) );
    attractor = new Attractor( 40.0, 30.0, 0.0 );
    receivingDock = new RectangularNode<Agent>( this, SHAPE_DRAW_2D3D, true,
    null, 270.0, 300.0, 0.0, 80.0, 60.0, 0.0,
            null, dodgerBlue, 4.0, LINE_STYLE_DASHED, POSITION_CHOICE_BY_ATTRACTORS, new PathEnd[] { new PathEnd(path, PathEndType.BEGIN)}, _receivingDock_attractors_xjal() );
    shippingDock = new RectangularNode<Agent>( this, SHAPE_DRAW_2D3D, true,
    null, 600.0, 300.0, 0.0, 80.0, 60.0, 0.0,
            null, lime, 4.0, LINE_STYLE_DASHED, POSITION_CHOICE_BY_ATTRACTORS, new PathEnd[] { new PathEnd(path, PathEndType.END)}, _shippingDock_attractors_xjal() );
  }

  @AnyLogicInternalCodegenAPI
  private void _createPersistentElementsAP0_xjal() {
    {
		storageSystem = new Storage( this, SHAPE_DRAW_2D3D, true,
				true,
				_storageSystem_controller_xjal, 400.0, 180.0, 0.0,
				RACK_TYPE_SELECTIVE,
				false,
				RACK_PLACEMENT_STAND_ALONE,
				1,
				10,
				1,
				0.0,
				3.0,
				14.0,
				1.0,
				0.10526315789473684,
				1.0,
				1.4,
				4.71238898038469,
				0.0,
				false,
				RACK_ODD_LEFT,
				lavender,
				dodgerBlue,
				true,
				2,
				true,
				10,
				1.0
				 );
    }
  }

  @AnyLogicInternalCodegenAPI
  private void _createPersistentElementsBS0_xjal() {
  }



  // Static initialization of persistent elements
  private void instantiatePersistentElements_xjal() {
    network = new com.anylogic.engine.markup.Network(this, "network", SHAPE_DRAW_2D3D, 0.0, true, true);  			
	_getNetworks_xjal = new INetwork[] { 
      network };
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
  public Main( Engine engine, Agent owner, AgentList<? extends Main> ownerPopulation ) {
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
    robots = instantiate_robots_xjal();
    sourceOrder = instantiate_sourceOrder_xjal();
    sinkOrder = instantiate_sinkOrder_xjal();
    storeInRack = instantiate_storeInRack_xjal();
    pickFromRack = instantiate_pickFromRack_xjal();
    _storageSystem_controller_xjal = instantiate__storageSystem_controller_xjal_xjal();
	instantiatePersistentElements_xjal();
    setupReferences_xjal();
  }

  @AnyLogicInternalCodegenAPI
  private void setupReferences_xjal() {
  }

  /**
   * Simple constructor. Please add created agent to some population by calling goToPopulation() function.
   */
  public Main() {
  }

  /**
   * Creating embedded object instances
   */
  @AnyLogicInternalCodegenAPI
  private void instantiatePopulations_xjal() {
  }

  @Override
  @AnyLogicInternalCodegenAPI
  public void doCreate() {
    super.doCreate();
    // Creating embedded object instances
    instantiatePopulations_xjal();
    // Assigning initial values for plain variables
    setupPlainVariables_Main_xjal();
Map<String, Set<?>> usdMapping = getRootAgent().ext(ExtRootModelAgent.class).getCustomObject(OmniverseHelper.USD_CONTEXT_COLLECTION_KEY,
()-> new LinkedHashMap<String, Set<?>>());
    // Dynamic initialization of persistent elements
    _createPersistentElementsAP0_xjal();
	_initialize_network_xjal();
	_initialize_level_xjal();
    level.initialize();
    presentation = new ShapeTopLevelPresentationGroup( Main.this, true, 0, 0, 0, 0 , level );
    presentation.getConfiguration3D().setBackgroundColor( silver );
    // Creating embedded object instances
    instantiatePopulations_xjal();
    icon = new ShapeModelElementsGroup( Main.this, getElementProperty( "model.Main.icon", IElementDescriptor.MODEL_ELEMENT_DESCRIPTORS )  );
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
    // Creating non-replicated embedded objects
    setupParameters_robots_xjal( robots, null );
    doBeforeCreate_robots_xjal( robots, null );
    robots.createAsEmbedded();
    setupParameters_sourceOrder_xjal( sourceOrder, null );
    doBeforeCreate_sourceOrder_xjal( sourceOrder, null );
    sourceOrder.createAsEmbedded();
    setupParameters_sinkOrder_xjal( sinkOrder, null );
    doBeforeCreate_sinkOrder_xjal( sinkOrder, null );
    sinkOrder.createAsEmbedded();
    setupParameters_storeInRack_xjal( storeInRack, null );
    doBeforeCreate_storeInRack_xjal( storeInRack, null );
    storeInRack.createAsEmbedded();
    setupParameters_pickFromRack_xjal( pickFromRack, null );
    doBeforeCreate_pickFromRack_xjal( pickFromRack, null );
    pickFromRack.createAsEmbedded();
    setupParameters__storageSystem_controller_xjal_xjal( _storageSystem_controller_xjal, null );
    doBeforeCreate__storageSystem_controller_xjal_xjal( _storageSystem_controller_xjal, null );
    _storageSystem_controller_xjal.createAsEmbedded();
	 // Port connectors with non-replicated objects
    storeInRack.in.connect( sourceOrder.out ); // connector
    sinkOrder.in.connect( pickFromRack.out ); // connector2
    pickFromRack.in.connect( storeInRack.out ); // connector3
    // Creating replicated embedded objects
    setupInitialConditions_xjal( Main.class );
    // Dynamic initialization of persistent elements
    _createPersistentElementsBS0_xjal();
  }

  @Override
  @AnyLogicInternalCodegenAPI
  public void doStart() {
    super.doStart();
    DailyUpdate.start();
    robots.startAsEmbedded();
    sourceOrder.startAsEmbedded();
    sinkOrder.startAsEmbedded();
    storeInRack.startAsEmbedded();
    pickFromRack.startAsEmbedded();
    _storageSystem_controller_xjal.startAsEmbedded();
  }


  /**
   * Assigning initial values for plain variables<br>
   * <em>This method isn't designed to be called by user and may be removed in future releases.</em>
   */
  @AnyLogicInternalCodegenAPI
  public void setupPlainVariables_xjal() {
    setupPlainVariables_Main_xjal();
  }

  /**
   * Assigning initial values for plain variables<br>
   * <em>This method isn't designed to be called by user and may be removed in future releases.</em>
   */
  @AnyLogicInternalCodegenAPI
  private void setupPlainVariables_Main_xjal() {
    inventory = 
100 
;
    order_quantity = 
0 
;
    day_index = 
0 
;
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

  public List<Object> getEmbeddedObjects() {
    List<Object> list = super.getEmbeddedObjects();
    if (list == null) {
      list = new LinkedList<>();
    }
    list.add( robots );
    list.add( sourceOrder );
    list.add( sinkOrder );
    list.add( storeInRack );
    list.add( pickFromRack );
    list.add( _storageSystem_controller_xjal );
    return list;
  }

  public AgentList<? extends Main> getPopulation() {
    return (AgentList<? extends Main>) super.getPopulation();
  }

  public List<? extends Main> agentsInRange( double distance ) {
    return (List<? extends Main>) super.agentsInRange( distance );
  }

  @AnyLogicInternalCodegenAPI
  public void onDestroy() {
    DailyUpdate.onDestroy();
    robots.onDestroy();
    sourceOrder.onDestroy();
    sinkOrder.onDestroy();
    storeInRack.onDestroy();
    pickFromRack.onDestroy();
    _storageSystem_controller_xjal.onDestroy();
    super.onDestroy();
  }

  @AnyLogicInternalCodegenAPI
  @Override
  public void doFinish() {
    super.doFinish();
    robots.doFinish();
    sourceOrder.doFinish();
    sinkOrder.doFinish();
    storeInRack.doFinish();
    pickFromRack.doFinish();
    _storageSystem_controller_xjal.doFinish();
  }


}
