from django.db.models import Q


class FilterableQuerysetMixin:
    """
    Mixin to provide common filtering functionality for querysets.
    Reduces code duplication in ViewSets that need query parameter filtering.
    """
    
    def get_queryset(self):
        """
        Returns filtered queryset based on query parameters.
        Override filter_fields in subclasses to specify which fields to filter.
        """
        qs = super().get_queryset()
        
        # Apply filters based on query parameters
        for field in getattr(self, 'filter_fields', []):
            value = self.request.query_params.get(field)
            if value:
                qs = qs.filter(**{f"{field}__iexact": value})
        
        return qs


class UserSpecificQuerysetMixin:
    """
    Mixin to provide user-specific queryset filtering.
    Ensures users can only access their own data, while admins can access all.
    """
    
    def get_queryset(self):
        """
        Returns queryset filtered by user ownership.
        Requires the model to have a 'user' field or similar relationship.
        """
        qs = super().get_queryset()
        
        # Admin/staff can see all records
        if self.request.user.is_staff or self.request.user.is_superuser:
            return qs
        
        # Regular users can only see their own records
        user_field = getattr(self, 'user_field', 'user')
        return qs.filter(**{user_field: self.request.user})


class ActiveOnlyQuerysetMixin:
    """
    Mixin to filter querysets to show only active records.
    Assumes the model has an 'is_active' field.
    """
    
    def get_queryset(self):
        """
        Returns only active records from the queryset.
        """
        qs = super().get_queryset()
        return qs.filter(is_active=True)


class OrderedQuerysetMixin:
    """
    Mixin to provide default ordering for querysets.
    """
    
    def get_queryset(self):
        """
        Returns ordered queryset based on default_ordering.
        Override default_ordering in subclasses to specify ordering.
        """
        qs = super().get_queryset()
        ordering = getattr(self, 'default_ordering', ['-created_at'])
        return qs.order_by(*ordering)


class SearchableQuerysetMixin:
    """
    Mixin to provide search functionality for querysets.
    """
    
    def get_queryset(self):
        """
        Returns queryset with search functionality.
        Override search_fields in subclasses to specify which fields to search.
        """
        qs = super().get_queryset()
        search_query = self.request.query_params.get('search')
        
        if search_query:
            search_fields = getattr(self, 'search_fields', [])
            if search_fields:
                q_objects = Q()
                for field in search_fields:
                    q_objects |= Q(**{f"{field}__icontains": search_query})
                qs = qs.filter(q_objects)
        
        return qs


class UserFilterableQuerysetMixin(UserSpecificQuerysetMixin, FilterableQuerysetMixin, OrderedQuerysetMixin):
    """
    Combined mixin for user-specific views with filtering and ordering.
    """
