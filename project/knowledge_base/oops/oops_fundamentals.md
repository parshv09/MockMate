# Object-Oriented Programming (OOP) Fundamentals

## 1. Core Pillars of OOP
- **Encapsulation:** Bundling internal data (fields) and methods that operate on that data into a single unit (class), while restricting direct access using access modifiers. Prevents unintended external interference and preserves object invariant integrity.
- **Abstraction:** Exposing essential domain features while hiding low-level implementation mechanics. Achieved via interfaces and abstract classes, enabling modular decoupling.
- **Inheritance:** An "is-a" relationship where a derived child class inherits attributes and behaviors from a base parent class, facilitating code reusability. Overuse can lead to brittle class hierarchies.
- **Polymorphism:** The ability of entities to take on multiple forms:
  - *Compile-Time (Static):* Method overloading (methods in same class with same name but distinct signatures) resolved during compilation.
  - *Runtime (Dynamic):* Method overriding where a subclass provides a specialized implementation of an inherited parent method, resolved dynamically at runtime via virtual method tables (dynamic dispatch).

## 2. SOLID Design Principles
- **S — Single Responsibility Principle (SRP):** A class should have only one reason to change, encapsulating a single well-defined responsibility.
- **O — Open/Closed Principle (OCP):** Software artifacts should be open for extension but closed for modification (e.g., adding behavior via inheritance or strategy implementations rather than altering existing code).
- **L — Liskov Substitution Principle (LSP):** Subtypes must be substitutable for their base types without breaking client expectations or correctness.
- **I — Interface Segregation Principle (ISP):** Clients should not be forced to depend upon interface methods they do not utilize; prefer narrow, role-specific interfaces over bloated ones.
- **D — Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions rather than concrete low-level implementations. Inversion of Control (IoC) and Dependency Injection (DI) materialize this principle.

## 3. Essential Design Patterns
- **Singleton (Creational):** Ensures a class has only one instance and provides a global access point. Thread safety requires double-checked locking with volatile references or initialization-on-demand holder idiom.
- **Factory Method (Creational):** Defines an interface for object creation, delegating concrete class instantiation to specialized subclasses. Decouples client callers from concrete class constructors.
- **Observer (Behavioral):** Defines a one-to-many publish-subscribe dependency. When a subject changes state, all registered observers are notified automatically (e.g., event listeners, reactive streams).
- **Strategy (Behavioral):** Encapsulates a family of interchangeable algorithms inside separate classes implementing a shared interface, allowing algorithms to vary independently from clients using them.

## 4. Software Architecture Principles
- **Composition vs. Inheritance:** Favor object composition ("has-a") over class inheritance ("is-a"). Composition provides runtime flexibility, lower coupling, and shields against fragile base class dilemmas.
- **Coupling vs. Cohesion:**
  - *High Cohesion:* Modules focus tightly on related tasks, making systems maintainable and testable.
  - *Low Coupling:* Modules maintain minimal dependencies on other modules, preventing cascading change failures.
- **DRY (Don't Repeat Yourself):** Every piece of knowledge or business logic must have a single, unambiguous representation within a system.
- **KISS (Keep It Simple, Stupid):** Prioritize simplicity in design; avoid over-engineering solutions beyond current requirements.
- **YAGNI (You Aren't Gonna Need It):** Implement functionality only when needed, never in anticipation of speculative future requirements.
