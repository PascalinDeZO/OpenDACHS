==============
Ticket Manager
==============

The `ticket_manager` module is the program's most important module. It provides the `TicketManager`, which manages
the tickets corresponding to the OpenDACHS requests. Such a ticket is associated with a flag, that is either
'submitted' (the user submitted the request, but has not confirmed it yet), 'confirmed' (the user confirmed the request, but
it has not yet been further processed), 'accepted' (the request has been processed and finalized) or 'denied' (the
request has been processed and denied). Furthermore, the ticket will be marked as 'deleted' when its lifespan is at its
end, so that it will be cleaned up. This happens if the ticket has expired (only tickets whose flag is 'submitted' can
expire), or it has been either been succesfully processed or been denied.

.. automodule:: src.ticket_manager
    :members: