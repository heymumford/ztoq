C4 Diagrams with Lucidchart
===========================

C4 Model
--------

The C4 model is a way to visualize software architecture using a set of hierarchical diagrams:

1. **Context diagram**: Shows the system in its environment
2. **Container diagram**: Shows the high-level technology choices
3. **Component diagram**: Shows how a container is made up of components
4. **Code diagram**: Shows how a component is implemented

Creating C4 Diagrams in Lucidchart
----------------------------------

Follow these steps to create C4 diagrams in Lucidchart:

1. Sign up or log in to `Lucidchart <https://www.lucidchart.com/>`_
2. Create a new document
3. Search for "C4" in the shape library sidebar
4. Add the C4 Model shape library
5. Use the shapes to create your diagrams

C4 Model Templates
-------------------

Here are some Lucidchart templates to get you started:

1. `C4 Context Diagram Template <https://lucid.app/lucidchart/templates/c4-context-diagram>`_
2. `C4 Container Diagram Template <https://lucid.app/lucidchart/templates/c4-container-diagram>`_
3. `C4 Component Diagram Template <https://lucid.app/lucidchart/templates/c4-component-diagram>`_

Example C4 Diagram Code
------------------------

Here's an example of how you might structure a C4 diagram in code (using PlantUML):

.. code-block:: text

    @startuml C4_Context
    !include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml

    Person(user, "User", "A user who wants to extract test data")
    System(ztoq, "ZTOQ", "Extracts test data from Zephyr Scale API")
    System_Ext(zephyr, "Zephyr Scale", "Test management system")
    
    Rel(user, ztoq, "Uses")
    Rel(ztoq, zephyr, "Extracts data from")
    
    @enduml

When you create your diagrams in Lucidchart, you can export them as images or as SVGs to include in your documentation.