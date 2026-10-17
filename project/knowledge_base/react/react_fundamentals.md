# React Fundamentals

## 1. Components: Functional vs. Class
- **Functional Components:** Standard modern syntax using functions returning JSX. Utilizes React Hooks for state and lifecycles without `this` binding.
- **Class Components:** Legacy syntax extending `React.Component` with lifecycle methods (`componentDidMount`, `componentDidUpdate`, `componentWillUnmount`) and `this.state`.

## 2. JSX and Rendering Architecture
- **JSX:** XML-like syntax compiled by Babel to `React.createElement()` calls, producing Virtual DOM objects.
- **Syntax Rules:** Must return a single root or Fragment `<>...</>`, use camelCase attributes (`className`, `htmlFor`), and embed JavaScript expressions inside `{}`.

## 3. Props vs. State
- **Props:** Read-only inputs passed from parent to child in a unidirectional flow; cannot be mutated by the receiver.
- **State:** Component-managed internal state. State setter calls schedule re-renders.
- **Lifting State Up:** Moving shared state to the nearest common ancestor to synchronize sibling components.

## 4. Essential React Hooks
- **useState:** Declares reactive state: `const [val, setVal] = useState(init)`. Use functional updater `setVal(prev => prev + 1)` for state dependent on previous values.
- **useEffect:** Manages side-effects. Runs on every render (no array), on mount only (`[]`), or when specified dependencies change (`[deps]`). Returning a cleanup function tears down subscriptions before re-running or unmounting.
- **useContext:** Accesses React Context data directly, bypassing multi-level prop drilling.
- **useRef:** Returns a mutable reference `{ current: val }` persisting across renders without causing re-renders; used for DOM access and instance values.
- **useMemo:** Memoizes expensive computation outputs based on dependency changes.
- **useCallback:** Memoizes function instances to avoid re-rendering memoized child components (`React.memo`).

## 5. Virtual DOM, Reconciliation, and Keys
- **Virtual DOM:** Lightweight in-memory representation of the DOM synced via ReactDOM.
- **Diffing Algorithm:** Employs an $O(n)$ heuristic assuming distinct component types generate different subtrees.
- **Keys in Lists:** Unique, stable identifiers across renders. Avoid array indices as keys because reordering or deleting items breaks state tracking.

## 6. Controlled vs. Uncontrolled Components
- **Controlled:** Form input values are tied to React state via `value` and updated through `onChange`.
- **Uncontrolled:** Form state remains inside DOM nodes and is accessed on-demand using `useRef`.

## 7. Client-Side Routing (React Router)
- **Routing:** Manages client-side navigation without full page reloads.
- **API Elements:** `<BrowserRouter>`, `<Routes>`, `<Route>`, `<Link>` for navigation, `useNavigate()` for programmatic redirects, and `useParams()` for path parameters.
