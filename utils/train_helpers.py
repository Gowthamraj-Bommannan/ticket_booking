import logging
import heapq
from datetime import datetime, timedelta
from django.db.models import Q
from routes.models import RouteEdge
from exceptions.handlers import NotFoundException, AlreadyExistsException
from utils.constants import RouteMessage, TrainMessage

logger = logging.getLogger("trains")


class TrainPathfindingHelpers:
    """
    Reusable pathfinding and route calculation helpers for train operations.
    Centralizes complex pathfinding logic to reduce redundancy.
    """
    
    @staticmethod
    def find_shortest_path(code_a, code_b):
        """
        Dijkstra's algorithm to find shortest path and total distance
        between two stations.
        
        Args:
            code_a (str): Source station code
            code_b (str): Destination station code
            
        Returns:
            tuple: (path, total_distance) or (None, None) if no path exists
        """
        # Build graph with single query
        edges = RouteEdge.objects.filter(is_active=True).select_related('from_station', 'to_station')
        graph = {}
        
        for edge in edges:
            from_code = edge.from_station.code.upper()
            to_code = edge.to_station.code.upper()
            
            graph.setdefault(from_code, []).append((to_code, edge.distance))
            if edge.is_bidirectional:
                graph.setdefault(to_code, []).append((from_code, edge.distance))
        
        # Dijkstra's algorithm
        queue = [(0, code_a.upper(), [code_a.upper()])]
        visited = set()
        
        while queue:
            dist, current, path = heapq.heappop(queue)
            if current == code_b.upper():
                return path, dist
            if current in visited:
                continue
            visited.add(current)
            
            for neighbor, weight in graph.get(current, []):
                if neighbor not in visited:
                    heapq.heappush(queue, (dist + weight, neighbor, path + [neighbor]))
        
        return None, None
    
    @staticmethod
    def calculate_distances(route_template, stop_codes):
        """
        Calculate distances between consecutive stops.
        Optimized to handle both fast and local train types.
        
        Args:
            route_template: RouteTemplate instance
            stop_codes (list): List of station codes
            
        Returns:
            list: List of distances between consecutive stops
            
        Raises:
            RouteStopsNotFoundException: If route not found between stations
        """
        is_fast = (
            hasattr(route_template, "category")
            and getattr(route_template, "category", "").lower() == "fast"
        )
        
        distances = []
        
        if is_fast:
            # For each consecutive pair, find shortest path and sum distances
            for stop in range(len(stop_codes) - 1):
                code_a = stop_codes[stop]
                code_b = stop_codes[stop + 1]
                path, total_distance = TrainPathfindingHelpers.find_shortest_path(code_a, code_b)
                
                if path is None:
                    logger.error(f"No route found between {code_a} to {code_b} (fast train pathfinding)")
                    raise NotFoundException(RouteMessage.ROUTE_NOT_FOUND_BETWEEN)
                distances.append(total_distance)
        else:
            # Local: require direct edge
            for stop in range(len(stop_codes) - 1):
                code_a = stop_codes[stop]
                code_b = stop_codes[stop + 1]
                
                edge = RouteEdge.objects.filter(
                    (
                        Q(from_station__code__iexact=code_a, to_station__code__iexact=code_b)
                        | Q(from_station__code__iexact=code_b, to_station__code__iexact=code_a, is_bidirectional=True)
                    ),
                    is_active=True,
                ).first()
                
                if not edge:
                    logger.error(f"No route found between {code_a} to {code_b}")
                    raise NotFoundException(RouteMessage.ROUTE_NOT_FOUND_BETWEEN)
                distances.append(edge.distance)
        
        return distances


class TrainScheduleHelpers:
    """
    Reusable schedule generation and validation helpers for train operations.
    Centralizes schedule-related logic to reduce redundancy.
    """
    
    @staticmethod
    def generate_schedule_timings(stations, distances, start_time, speed=35, halt_min=1):
        """
        Generate arrival and departure times for each station in the route.
        
        Args:
            stations (list): List of station objects
            distances (list): List of distances between consecutive stations
            start_time: Start time of the journey
            speed (int): Speed in km/h (default: 35)
            halt_min (int): Halt time in minutes (default: 1)
            
        Returns:
            list: List of dictionaries with station timing information
        """
        result = []
        current_time = datetime.combine(datetime.today(), start_time)
        
        for idx, station in enumerate(stations):
            if idx == 0:
                # First station: only departure_time
                arrival = None
                departure = current_time
            else:
                # Travel from previous station
                travel_mins = (distances[idx - 1] / speed) * 60
                arrival = departure + timedelta(minutes=travel_mins)
                
                if idx == len(stations) - 1:
                    # Last station: only arrival_time
                    departure = None
                else:
                    departure = arrival + timedelta(minutes=halt_min)
            
            result.append({
                "station_code": station.code,
                "arrival_time": arrival.strftime("%H:%M") if arrival else None,
                "departure_time": departure.strftime("%H:%M") if departure else None,
            })
        
        return result
    
    @staticmethod
    def validate_schedule_conflicts(train, new_start, new_end, new_days, exclude_instance=None):
        """
        Validate schedule conflicts and overlaps.
        
        Args:
            train: Train instance
            new_start: Start time of new schedule
            new_end: End time of new schedule
            new_days (set): Set of days for new schedule
            exclude_instance: Instance to exclude from validation (for updates)
            
        Raises:
            ScheduleAlreadyExists: If schedule overlap detected
        """
        from trains.models import TrainSchedule
        
        existing_schedules = TrainSchedule.objects.filter(train=train, is_active=True)
        
        if exclude_instance:
            existing_schedules = existing_schedules.exclude(pk=exclude_instance.pk)
        
        for sched in existing_schedules:
            sched_days = set([d.strip() for d in sched.days_of_week.split(",")])
            if not (new_days & sched_days):
                continue  # No overlapping days
            
            sched_start = sched.start_time
            sched_end = None
            
            if sched.stops_with_time and len(sched.stops_with_time) > 0:
                sched_end = datetime.strptime(sched.stops_with_time[-1]["arrival_time"], "%H:%M").time()
            else:
                continue  # skip if no stops
            
            # Check for overlap regardless of direction
            if new_start < sched_end and sched_start < new_end:
                logger.error("Schedule overlap detected for train.")
                raise AlreadyExistsException(TrainMessage.TRAIN_SCHEDULE_OVERLAPS)
    
    @staticmethod
    def validate_direction_alternation(train, new_start, new_direction, route_template, exclude_instance=None):
        """
        Validate direction alternation and station continuity.
        
        Args:
            train: Train instance
            new_start: Start time of new schedule
            new_direction (str): Direction of new schedule
            route_template: RouteTemplate instance
            exclude_instance: Instance to exclude from validation (for updates)
            
        Raises:
            ScheduleAlreadyExists: If direction alternation validation fails
        """
        from trains.models import TrainSchedule
        
        existing_schedules = TrainSchedule.objects.filter(train=train, is_active=True)
        
        if exclude_instance:
            existing_schedules = existing_schedules.exclude(pk=exclude_instance.pk)
        
        # Find the latest schedule that ends before the new start time
        latest_prior_schedule = None
        for sched in existing_schedules.order_by("start_time"):
            if sched.stops_with_time and len(sched.stops_with_time) > 0:
                sched_end = datetime.strptime(sched.stops_with_time[-1]["arrival_time"], "%H:%M").time()
                if sched_end <= new_start:
                    latest_prior_schedule = sched
        
        if latest_prior_schedule:
            prev_direction = latest_prior_schedule.direction
            prev_last_station_code = latest_prior_schedule.route_template.stops[-1].strip().upper()
            new_first_station_code = route_template.stops[0].strip().upper()
            
            if prev_direction == new_direction:
                logger.error("Train cannot have two consecutive schedules in the same direction without a return trip.")
                raise AlreadyExistsException(TrainMessage.SCHEDULE_DIRECTION_NOT_BE_SAME)
            
            if prev_last_station_code != new_first_station_code:
                logger.error("Train's new schedule does not start from the previous journey's end station.")
                raise AlreadyExistsException(TrainMessage.TRAIN_SCHEDULE_MUST_BE_DIFFERENT) 